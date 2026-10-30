#include "gs_fg_trace.h"
#include <assert.h>
#include <stdio.h>
int Port_Setting(const char *s,int d){(void)s;(void)d;return 0;}
int main(void) {
 uint64_t src=GsFg_Source(1,2),gen=src|1;
 GsFg_Register(gen,0,src,FG_GENERATED,16666667);
 GsFg_Event(FG_DISPATCH,gen,1,2);
 GsFg_Event(FG_PRESENT,gen,0,0); /* accepted != complete */
 GsFgStats s;GsFg_Snapshot(&s);assert(s.dispatched==1 && s.completed==0 && s.presented==1 && s.uniquePresented==0);
 GsFg_Proof(gen,1);GsFg_Event(FG_COMPLETE,gen,2000000,2);
 GsFg_Snapshot(&s);assert(s.completed==1 && s.generatedPresented==1 && s.uniquePresented==1);
 /* Repeated callbacks must never inflate counts. */
 GsFg_Event(FG_COMPLETE,gen,2000000,2);GsFg_Event(FG_PRESENT,gen,0,0);GsFg_Proof(gen,1);
 GsFg_Event(FG_DISPLAY,gen,123,0);GsFg_Event(FG_DISPLAY,gen,123,0);
 GsFg_Snapshot(&s);assert(s.completed==1 && s.generatedPresented==1 && s.displayed==1);
 /* A generated image completed but its real Vulkan present failed. */
 gen=src|2;GsFg_Register(gen,0,src,FG_GENERATED,0);GsFg_Event(FG_DISPATCH,gen,2,3);
 GsFg_Proof(gen,1);GsFg_Event(FG_COMPLETE,gen,1000,2);
 GsFg_Event(FG_PRESENT,gen,-1000001004,0);GsFg_Event(FG_DROP,gen,8,0);
 GsFg_Snapshot(&s);assert(s.completed==2 && s.presented==1 && s.generatedPresented==1 && s.dropped==1 && s.presentFailed==1);
 /* A source-only hard-cut copy is not a generated temporal image. */
 gen=src|3;GsFg_Register(gen,0,src,FG_GENERATED,0);GsFg_Event(FG_DISPATCH,gen,1,2);
 GsFg_Proof(gen,3);GsFg_Event(FG_COMPLETE,gen,1000,2);GsFg_Event(FG_PRESENT,gen,1000001003,0);
 GsFg_Snapshot(&s);assert(s.completed==2 && s.generatedPresented==1 && s.presented==2);
 /* An exact sampled repeat is computed but adds no unique presentation. */
 src=GsFg_Source(2,4);gen=src|1;GsFg_Register(gen,0,src,FG_GENERATED,0);
 GsFg_Event(FG_DISPATCH,gen,1,2);GsFg_Proof(gen,0);GsFg_Event(FG_COMPLETE,gen,1000,2);GsFg_Event(FG_PRESENT,gen,0,0);
 GsFg_Snapshot(&s);assert(s.completed==3 && s.generatedPresented==1 && s.repeats==1);
 /* Rollback bookkeeping is visual only. */
 GsFg_Rollback(8);GsFg_ResimTick();GsFg_Snapshot(&s);assert(s.epoch==1 && s.resimTicks==1);
 GsFg_Event(FG_SOURCE_COMPLETE,src,0,0);GsFg_Event(FG_SOURCE_COMPLETE,src,0,0);
 GsFg_Snapshot(&s);assert(s.real==1);
 puts("PASS FG ledger: GPU completion, raw/unique/generated presents, VkResult failures, repeats, cuts, independent display feedback, rollback, deduplication");
}
