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
 /* The proof's command may retire before the source command. It must not
    swallow the real-source fence count (the opt6 device log did this). */
 src=GsFg_Source(3,6);GsFg_Proof(src,1);GsFg_Event(FG_COMPLETE,src,10,3);
 GsFg_Event(FG_SOURCE_COMPLETE,src,0,0);GsFg_Event(FG_SOURCE_COMPLETE,src,0,0);
 GsFg_Snapshot(&s);assert(s.real==2 && s.captured==3);
 /* Driver-observed generated images require distinct completed content.
    A physical callback can arrive before proof/complete; deduplicate later. */
 gen=src|1;GsFg_Register(gen,0,src,FG_GENERATED,0);
 GsFg_Event(FG_DISPLAY,gen,2000000000,0);GsFg_Proof(gen,1);GsFg_Event(FG_COMPLETE,gen,100,2);
 GsFg_Event(FG_DISPLAY,gen,2000000000,0);GsFg_Snapshot(&s);assert(s.generatedDisplayed==2);
 /* Batched driver reports use actualPresentTime, not CPU delivery rate. */
 for(int i=0;i<66;i++){uint64_t id=GsFg_Source(10+(unsigned)i,200+(unsigned)i);GsFg_Event(FG_DISPLAY,id,1000000000ll+(int64_t)i*16666667ll,0);}
 GsFg_Snapshot(&s);assert(s.displayHzMilli>=59999 && s.displayHzMilli<=60001);
 puts("PASS FG ledger: GPU completion, raw/unique/generated presents, VkResult failures, repeats, cuts, independent display feedback, rollback, deduplication");
}
