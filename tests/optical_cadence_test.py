#!/usr/bin/env python3
"""Reproduce the actual opt6 device failure through production frame planning."""
from pathlib import Path
import os,re,subprocess,sys,tempfile
root=Path(sys.argv[1]);source=(root/'port/src/gs/gs_draw.c').read_text()
def function(name):
    m=re.search(r'^static (?:int|void) '+name+r'\([^;]*?\)\s*\{',source,re.M);assert m,name
    end=source.index('{',m.start())+1;depth=1
    while depth:depth+=(source[end]=='{')-(source[end]=='}');end+=1
    return source[m.start():end]
prefix=r'''
#include <assert.h>
#include <stdio.h>
#include <stdint.h>
#include "gs_perf.h"
static DrOpticalCadence sOpticalCadence;
static uint64_t sOpticalCadenceEpoch,sInterpTickNs;
static unsigned sInterpLastBlank,blank;
static int gsInterp=2,sInterpCap=4,sInterpSteps,thermal,gPortInMenus;
static uint64_t epoch,blankNs=16683350ull*100/114;
static unsigned refresh=60000;
int GsPerf_Thermal(void){return thermal;}
unsigned GsPerf_RefreshMilliHz(void){return refresh;}
unsigned Gs_RenderBlank(void){return blank;}
uint64_t Gs_RenderEpoch(void){return epoch;}
unsigned long long Port_BlankNs(void){return blankNs;}
'''
main=r'''
static void reset(void){sOpticalCadence=(DrOpticalCadence){0};blank=sInterpLastBlank=0;epoch=sOpticalCadenceEpoch=0;}
int main(void){
 unsigned images=0,generated=0,old=0,first[16];
 for(int i=0;i<10000;i++) {
  blank+=2;interp_select_steps(1);assert(sInterpSteps>=1 && sInterpSteps<=2);
  assert(sInterpTickNs/(unsigned)sInterpSteps>=16666667ull);
  images+=(unsigned)sInterpSteps;generated+=(unsigned)sInterpSteps-1;
  old+=(unsigned)DrTickDisplaySteps(2,60000,2*blankNs);
  if(i<16)first[i]=(unsigned)sInterpSteps;
 }
 uint64_t fit=10000ull*2*blankNs*60000/1000000000000ull;
 assert(images==fit && old==10000 && generated>7500);
 printf("PASS production replay opt6 settings: 114%% / 60Hz / 10000 sources: old generated=0, planned generated=%u images=%u capacity=%llu\n",generated,images,(unsigned long long)fit);
 printf("slot sequence:");for(int i=0;i<16;i++)printf(" %u",first[i]);puts("");
 /* Render every other tick: credit reflects the last two visible images,
    instead of throwing away optical history and assuming 34 real fps. */
 reset();images=0;
 for(int i=0;i<1000;i++){blank+=4;interp_select_steps(1);assert(sInterpSteps>=3 && sInterpSteps<=4);images+=(unsigned)sInterpSteps;}
 assert(images==1000ull*4*blankNs*60000/1000000000000ull);
 /* Fixed display targets, FG limits, thermal, menus, refresh changes. */
 for(unsigned hz=30000;hz<=120000;hz+=30000){
  reset();blankNs=16666667;refresh=hz;
  for(int i=0;i<120;i++){blank+=2;interp_select_steps(1);assert(sInterpSteps==(int)(hz/30000));}
 }
 reset();refresh=60000;sInterpCap=1;blank+=2;interp_select_steps(1);assert(sInterpSteps==1);
 sInterpCap=4;thermal=3;blank+=2;interp_select_steps(1);assert(sInterpSteps==1);thermal=0;
 gPortInMenus=1;blank+=2;interp_select_steps(1);assert(sInterpSteps==1);gPortInMenus=0;
 /* A rewind drops fractional phase and a backwards blank is not a huge gap. */
 epoch++;blank=3;interp_select_steps(1);assert(sInterpSteps==2 && sOpticalCadenceEpoch==epoch);
 /* Legacy geometry policy remains unchanged and the simulation clock is read-only. */
 blank=5;interp_select_steps(0);assert(sInterpSteps==2 && blank==5);
 puts("PASS visible source gaps, 30/60/90/120Hz, bounded slots, thermal, rollback phase, unchanged simulation");
}
'''
with tempfile.TemporaryDirectory() as tmp:
    p=Path(tmp);(p/'test.c').write_text(prefix+function('interp_steps')+function('interp_select_steps')+main)
    subprocess.run(['cc','-std=gnu11','-D__ANDROID__','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
        '-I'+str(root/'port/src/gs'),str(p/'test.c'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0'})
