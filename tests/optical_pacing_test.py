#!/usr/bin/env python3
"""Compile and exercise the production scheduler functions with a deterministic clock."""
from pathlib import Path
import os, subprocess, sys, tempfile
root=Path(sys.argv[1]);source=(root/'port/src/gs/gs_draw.c').read_text()
def function(name, text=source):
    import re
    match=re.search(r'^(?:static )?(?:int|void|uint64_t) '+name+r'\([^;]*?\)\s*\{',text,re.M)
    assert match,name
    pos=match.start();start=pos
    opening=text.index('{',pos);depth=1;end=opening+1
    while depth:
        depth+=(text[end]=='{')-(text[end]=='}');end+=1
    return text[start:end]
prefix=r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
static int sInterpNext,sInterpSteps,sInterpRepeat,sInterpOptical=1;
static uint64_t sInterpBlendShown,sInterpTickNs,sInterpBlendTook,clockNs;
unsigned long long gPortSleptNs;
static volatile int sInterpHurry;
static unsigned gsDrawCount,gsVertCount,gsVuVertCount,gsVuIdxCount,gsVuUniCount;
static void *sBackend=(void*)1;
static int restore,remember,shown[4],shownCount,threaded,onThread,epochValid=1,dropped;
static uint64_t times[4];
static int gsPendingScale4,scaleApplied,labelsApplied,sGpu=1;
static unsigned sStat[1];
static void scale_apply(void) {scaleApplied++;gsPendingScale4=0;}
static void menu_labels_apply(void) {labelsApplied++;}
static void vif(const uint32_t *p,unsigned words) {(void)p;(void)words;clockNs+=1000000;}
static uint64_t gpu_now(void) { return clockNs; }
static void interp_counts_restore(void) { restore++; }
static void interp_remember(void) { remember++; }
static void interp_show(int n) { times[shownCount]=clockNs;shown[shownCount++]=n; }
static int Gs_RenderThreaded(void) { return threaded; }
static int Gs_OnRenderThread(void) { return onThread; }
static void SDL_DelayPrecise(uint64_t n) { clockNs+=n; }
static uint64_t GsFg_EarliestNs(void){return 0;}
int GsVkOptical_EpochValid(void){return epochValid;}
void GsVkOptical_Reset(int release){(void)release;}
void GsVkOptical_DropRange(int first,int last,int reason){(void)reason;if(last>=first)dropped+=last-first+1;}
void PortInput_Pump(void) {}
int Port_VBlankUsLeft(void) { return 500; }
'''
functions='\n'.join(function(n) for n in ('interp_show_next','interp_due','GsGpu_InterpHurry','GsGpu_InterpRun','GsGpu_InterpPump',
                                       'GsGpu_OpticalPoll','GsGpu_OpticalBeginList','interp_source_flush'))
functions+='\n'+function('chain_block',(root/'port/src/gs/gs_core.c').read_text())
main=r'''
static void setup(int steps) {
 sInterpSteps=steps;sInterpNext=2;sInterpRepeat=0;sInterpBlendShown=1000000000;
 sInterpTickNs=33333333;sInterpBlendTook=0;clockNs=sInterpBlendShown;
 shownCount=restore=remember=threaded=onThread=0;sInterpHurry=0;epochValid=1;dropped=0;
 gPortSleptNs=0;
 sInterpOptical=1;gsPendingScale4=scaleApplied=labelsApplied=0;sStat[0]=0;
 gsDrawCount=17;gsVertCount=53;gsVuUniCount=3; /* next CPU list is already being built */
}
int main(void) {
 for(int n=2;n<=4;n++) {
  setup(n);
  for(int k=2;k<=n;k++) {
   uint64_t due=sInterpBlendShown+(uint64_t)(k-1)*(sInterpTickNs/n);
   clockNs=due-1;GsGpu_InterpPump(0,0);assert(shownCount==k-2);
   clockNs=due;GsGpu_InterpPump(0,0);assert(shownCount==k-1);
   assert(shown[k-2]==k && times[k-2]==due);
  }
  assert(sInterpNext==0 && !restore && !remember);
  assert(gsDrawCount==17 && gsVertCount==53 && gsVuUniCount==3);
  setup(n);GsGpu_InterpRun();assert(shownCount==n-1 && shown[n-2]==n && !restore);
  setup(n);GsGpu_InterpHurry(1);GsGpu_InterpRun();assert(shownCount==1 && shown[0]==n);
  setup(n);GsGpu_InterpPump(0,1);assert(shownCount==1 && shown[0]==n && !restore);
 }
 setup(4);threaded=1;GsGpu_InterpPump(100,0);assert(shownCount==0);
 setup(4);GsGpu_InterpPump(-1,0);assert(shownCount==0); /* do not delay a simulation blank */
 setup(2);clockNs=interp_due()-2000000;GsGpu_InterpPump(6,0);
 assert(shownCount==1 && gPortSleptNs==2000000); /* pacing is excluded from source work */
 setup(2);threaded=onThread=1;clockNs=interp_due()-2000000;GsGpu_InterpPump(6,0);
 assert(shownCount==1 && !gPortSleptNs); /* render-thread wait overlaps simulation */
 for(int n=2;n<=4;n++) {
  setup(n);
  /* Real DMA decoder polls during 25 ms of new-list work, no VBlank available. */
  uint32_t words[4]={0};clockNs+=5000000;
  for(int b=0;b<25;b++)chain_block(words,words,1,0);
  interp_source_flush(); /* hand-over of the next source must retain old endpoint */
  assert(shownCount==n-1 && shown[n-2]==n && !sInterpNext && !restore);
  assert(gsDrawCount==17 && gsVertCount==53 && gsVuUniCount==3);
  for(int k=0;k<n-1;k++)assert(times[k]<=sInterpBlendShown+(uint64_t)(k+1)*(sInterpTickNs/n)+1000000);
  /* If decoding could not poll, flush still presents the real once, before overwrite. */
  setup(n);interp_source_flush();assert(shownCount==1 && shown[0]==n && !sInterpNext);
 }
 setup(2);gsDrawCount=gsVertCount=gsVuUniCount=0;gsPendingScale4=8;GsGpu_OpticalBeginList();
 assert(shownCount==1 && !sInterpNext && scaleApplied==1 && labelsApplied==1);
 setup(2);GsGpu_OpticalBeginList();assert(!shownCount && !scaleApplied);
 setup(2);sInterpOptical=0;interp_source_flush();assert(!shownCount && !sInterpNext);
 setup(4);sInterpNext=4;setenv("BT3_INTERP_ONLY","1",1);
 assert(interp_show_next()==0 && !restore && !remember && gsDrawCount==17);
 unsetenv("BT3_INTERP_ONLY");
 setup(4);epochValid=0;GsGpu_InterpPump(100,0);assert(!shownCount && !sInterpNext && dropped==2);
 setup(4);clockNs+=50000000;GsGpu_InterpPump(0,0);assert(shownCount==1 && shown[0]==4 && dropped==2);
 puts("PASS production optical scheduler: 2x/3x/4x deadlines, DMA polling, endpoint before overwrite, thread ownership, untouched next CPU list");
}
'''
with tempfile.TemporaryDirectory() as tmp:
    p=Path(tmp);(p/'test.c').write_text(prefix+functions+main)
    subprocess.run(['cc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0'})
