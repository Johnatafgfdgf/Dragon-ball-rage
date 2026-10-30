#!/usr/bin/env python3
"""Compile and exercise the production scheduler functions with a deterministic clock."""
from pathlib import Path
import os, subprocess, sys, tempfile
root=Path(sys.argv[1]);source=(root/'port/src/gs/gs_draw.c').read_text()
def function(name):
    pos=source.index(name+'(')
    start=source.rfind('\n',0,pos)+1
    opening=source.index('{',pos);depth=1;end=opening+1
    while depth:
        depth+=(source[end]=='{')-(source[end]=='}');end+=1
    return source[start:end]
prefix=r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
static int sInterpNext,sInterpSteps,sInterpRepeat,sInterpOptical=1;
static uint64_t sInterpBlendShown,sInterpTickNs,sInterpBlendTook,clockNs;
static volatile int sInterpHurry;
static unsigned gsDrawCount,gsVertCount,gsVuVertCount,gsVuIdxCount,gsVuUniCount;
static void *sBackend=(void*)1;
static int restore,remember,shown[4],shownCount,threaded,onThread;
static uint64_t times[4];
static uint64_t gpu_now(void) { return clockNs; }
static void interp_counts_restore(void) { restore++; }
static void interp_remember(void) { remember++; }
static void interp_show(int n) { times[shownCount]=clockNs;shown[shownCount++]=n; }
static int Gs_RenderThreaded(void) { return threaded; }
static int Gs_OnRenderThread(void) { return onThread; }
static void SDL_DelayPrecise(uint64_t n) { clockNs+=n; }
void PortInput_Pump(void) {}
int Port_VBlankUsLeft(void) { return 500; }
'''
functions='\n'.join(function(n) for n in ('interp_show_next','interp_due','GsGpu_InterpHurry','GsGpu_InterpRun','GsGpu_InterpPump'))
main=r'''
static void setup(int steps) {
 sInterpSteps=steps;sInterpNext=2;sInterpRepeat=0;sInterpBlendShown=1000000000;
 sInterpTickNs=33333333;sInterpBlendTook=0;clockNs=sInterpBlendShown;
 shownCount=restore=remember=threaded=onThread=0;sInterpHurry=0;
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
 setup(4);sInterpNext=4;setenv("BT3_INTERP_ONLY","1",1);
 assert(interp_show_next()==0 && !restore && !remember && gsDrawCount==17);
 puts("PASS production optical scheduler: 2x/3x/4x deadlines, hurry, native endpoint, thread ownership, untouched next CPU list");
}
'''
with tempfile.TemporaryDirectory() as tmp:
    p=Path(tmp);(p/'test.c').write_text(prefix+functions+main)
    subprocess.run(['cc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0'})
