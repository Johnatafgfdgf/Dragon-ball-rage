#!/usr/bin/env python3
"""Exercise production submit pacing with distinct SDL/monotonic origins."""
from pathlib import Path
import re,os,subprocess,sys,tempfile
r=Path(sys.argv[1]);s=(r/'port/src/gs/gs_fg_probe.c').read_text()
def function(name):
 m=re.search(r'^(?:uint64_t|int) '+name+r'\([^;]*?\)\s*\{',s,re.M);assert m
 i=s.index('{',m.start())+1;d=1
 while d:d+=(s[i]=='{')-(s[i]=='}');i+=1
 return s[m.start():i]
prefix=r'''
#include <stdint.h>
#include <assert.h>
#include <stdio.h>
#include "dr_vk_probe.h"
#include "gs_fg_trace.h"
typedef void SDL_GPUCommandBuffer;
static uint64_t nextPresent,pacingNs,presentId,clockNs=1000000000000000ull;
static unsigned pacingRefresh;
static int64_t presentResult;
static DrVkProbe probe;
static int active,have=1,requested=2,submitOK=1,drops,threaded,report;
static int64_t vkResult;
static uint64_t submitCost,seenTarget;
unsigned long long gPortSleptNs;
uint64_t GsFg_NowNs(void){return clockNs;}
uint64_t SDL_GetTicksNS(void){return clockNs-999999000000000ull;}
void SDL_DelayPrecise(uint64_t ns){clockNs+=ns+50000;}
unsigned GsPerf_RefreshMilliHz(void){return 60000;}
void GsPerf_FramegenGet(int *r,int *e,int *s){*r=requested;*e=requested;*s=1;}
int Gs_RenderThreaded(void){return threaded;}
int SDL_SubmitGPUCommandBuffer(SDL_GPUCommandBuffer *c){(void)c;seenTarget=probe.desiredPresentNs;clockNs+=submitCost;if(report){presentId=probe.image;presentResult=vkResult;}return submitOK;}
void GsFg_Deadline(uint64_t id,uint64_t due){(void)id;assert(due<=clockNs && due>900000000000000ull);}
void GsFg_Event(int stage,uint64_t id,int64_t value,uint64_t detail){(void)id;(void)value;(void)detail;if(stage==FG_DROP)drops++;}
'''
main=r'''
int main(void){
 uint64_t first=clockNs;
 assert(GsFg_Submit((void*)1,8,0));assert(nextPresent==first+16666667ull);
 assert(GsFg_EarliestNs()==nextPresent && seenTarget==first);
 assert(GsFg_Submit((void*)1,0,16));assert(clockNs==first && !pacingNs && !seenTarget);
 assert(GsFg_Submit((void*)1,17,0));assert(clockNs>=first+16666667ull && pacingNs==gPortSleptNs);
 uint64_t slept=gPortSleptNs;threaded=1;assert(GsFg_Submit((void*)1,24,0));assert(gPortSleptNs==slept);
 /* A slow vkQueuePresent return does not add that delay to every interval. */
 uint64_t phase=nextPresent;submitCost=1000000;
 for(int i=0;i<600;i++){assert(GsFg_Submit((void*)1,24,0));assert(seenTarget==phase+(uint64_t)i*16666667ull);}
 assert(nextPresent==phase+600ull*16666667ull);submitCost=0;
 requested=1;first=clockNs;assert(GsFg_Submit((void*)1,32,0));assert(clockNs==first && !nextPresent);
 /* SDL returning true is insufficient if no real present callback arrived. */
 active=1;assert(!GsFg_Submit((void*)1,40,0) && drops==1 && !have);
 report=1;vkResult=-1000001004ll;assert(!GsFg_Submit((void*)1,48,0) && drops==2);
 vkResult=1000001003ll;assert(GsFg_Submit((void*)1,56,0));
 puts("PASS production present pacing: monotonic origin, display interval, source-only no wait, work exclusion, VkResult vs SDL bool");
}
'''
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp);(p/'test.c').write_text(prefix+function('GsFg_EarliestNs')+function('GsFg_Submit')+main)
 subprocess.run(['cc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I'+str(r/'port/src/gs'),str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0'})
