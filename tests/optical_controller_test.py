#!/usr/bin/env python3
"""Exercise the production cost-controller entry points, not only the policy."""
from pathlib import Path
import os, subprocess, sys, tempfile
source=(Path(sys.argv[1])/'port/src/gs/gs_draw.c').read_text()
def function(name):
    pos=source.index(name+'(');start=source.rfind('\n',0,pos)+1
    opening=source.index('{',pos);depth=1;end=opening+1
    while depth:
        depth+=(source[end]=='{')-(source[end]=='}');end+=1
    return source[start:end]
prefix=r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "gs_perf.h"
static DrFramePolicy sFramePolicy;
static DrOpticalPolicy sOpticalPolicy;
static int sOpticalCostQuality=-1;
static int sInterpCap=4,gsInterp=1,sourceCap=4,thermal,adaptive=1,quality=1;
int gPortInMenus;
static uint64_t clockNs=1000000000ull;
static uint64_t gpu_now(void) { return clockNs; }
unsigned long long Port_BlankNs(void) { return 16683350ull; }
int Port_Setting(const char *key,int def) {
 return !strcmp(key,"dr_fg_auto") ? adaptive : !strcmp(key,"dr_fg_quality") ? quality : def;
}
int GsPerf_SourceCap(void) { return sourceCap; }
int GsPerf_Thermal(void) { return thermal; }
unsigned GsPerf_RefreshMilliHz(void) { return 120000; }
'''
main=r'''
int main(void) {
 for(int i=0;i<600;i++) {
  clockNs+=33366700;interp_optical_cost(1000000,1);interp_optical_cost(20000000,0);
  assert(sInterpCap==2);
 }
 /* The legacy replay path still uses its own cost policy. */
 for(int i=0;i<600;i++) { clockNs+=33366700;interp_cost(20000000); }
 assert(sInterpCap==1);
 /* Whole-source CPU overload remains a separate mandatory adaptive guard. */
 sourceCap=1;interp_optical_cost(20000000,0);assert(sInterpCap==1);
 sourceCap=4;
 for(int i=0;i<200;i++) { clockNs+=33366700;interp_optical_cost(20000000,0); }
 assert(sInterpCap==2);
 thermal=3;interp_optical_cost(20000000,0);assert(sInterpCap==1);
 thermal=0;adaptive=0;gsInterp=2;interp_optical_cost(20000000,0);assert(sInterpCap==4);
 gPortInMenus=1;interp_optical_cost(100000000,0);assert(!sOpticalPolicy.source.seen);
 gPortInMenus=0;quality=0;interp_optical_cost(20000000,0);
 assert(sOpticalCostQuality==0 && sOpticalPolicy.source.seen==0);
 sOpticalPolicy.extraNs=100000000;quality=1;interp_optical_cost(20000000,0);
 assert(sOpticalCostQuality==1 && !sOpticalPolicy.extraNs);
 puts("PASS production optical controller: independent source/extra costs, legacy path, source guard, thermal, menu reset");
}
'''
with tempfile.TemporaryDirectory() as tmp:
    p=Path(tmp);(p/'test.c').write_text(prefix+'\n'.join(function(n) for n in ('interp_steps','interp_cost','interp_optical_cost'))+main)
    subprocess.run(['cc','-std=gnu11','-D__ANDROID__','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
                    '-I'+str(Path(sys.argv[1])/'port/src/gs'),str(p/'test.c'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0'})
