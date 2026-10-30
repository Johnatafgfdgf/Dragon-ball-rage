#!/usr/bin/env python3
"""Compile the actual optical present wrapper with deterministic SDL callbacks."""
from pathlib import Path
import os,re,subprocess,sys,tempfile
root=Path(sys.argv[1]);s=(root/'port/src/gs/gs_gpu.c').read_text()
m=re.search(r'^int GsVkOptical_Present\([^;]*?\)\s*\{',s,re.M);assert m
start=m.start();i=s.index('{',start)+1;depth=1
while depth:depth+=(s[i]=='{')-(s[i]=='}');i+=1
prefix=r'''
#include <SDL3/SDL.h>
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "gs_optical.h"
#include "gs_fg_probe.h"
#include "gs_fg_trace.h"
#define SCALE 1
static int sTW=512,sTH=512;
static uint64_t sFgSource=8;
#define MAX_TARGETS 3
static DrOptical *sOptical=(DrOptical*)1;
static SDL_GPUDevice *sDev=(SDL_GPUDevice*)1;
static SDL_Window *sWindow=(SDL_Window*)1;
static SDL_GPUTexture *sTgCol[3]={(SDL_GPUTexture*)1};
static int sOptPair=1,sLastShown=0,events,liveUI,cachedUI,realImage,flowImage;
static int acquireOK=1,submitOK=1,commandOK=1,resets;
static unsigned nextDrawCount=17;
int GsVkOptical_EpochValid(void) {return 1;}
void GsVkOptical_DropRange(int a,int b,int c){(void)a;(void)b;(void)c;}
void GsVkOptical_Reset(int r){(void)r;}
void GsFg_Event(int a,uint64_t b,int64_t c,uint64_t d){(void)a;(void)b;(void)c;(void)d;}
void GsFg_InvalidateProof(void){}
void GsFg_Compute(uint64_t a,int b){(void)a;(void)b;}
void GsFg_Verify(SDL_GPUCommandBuffer *c,SDL_GPUTexture *t,Uint32 a,Uint32 b,Uint32 d,Uint32 e,uint64_t id,int gen,SDL_GPUTexture *cut){(void)c;(void)t;(void)a;(void)b;(void)d;(void)e;(void)id;(void)gen;(void)cut;}
SDL_GPUTexture *DrOptical_Scene(const DrOptical *f){(void)f;return NULL;}
int GsFg_Submit(SDL_GPUCommandBuffer *c,uint64_t i,uint64_t s){(void)i;(void)s;return SDL_SubmitGPUCommandBuffer(c);}
static int window_ready(void) {return 1;}
static void poll_events(void) {events++;}
static void present_apply(void) {}
int Port_Setting(const char *key,int def) {(void)key;return def;}
Uint64 SDL_GetTicksNS(void) {static Uint64 t;t+=1000;return t;}
SDL_GPUCommandBuffer *SDL_AcquireGPUCommandBuffer(SDL_GPUDevice *d) {(void)d;return commandOK?(SDL_GPUCommandBuffer*)1:NULL;}
bool SDL_WaitAndAcquireGPUSwapchainTexture(SDL_GPUCommandBuffer *c,SDL_Window *w,SDL_GPUTexture **t,Uint32 *x,Uint32 *y) {
 (void)c;(void)w;*t=acquireOK?(SDL_GPUTexture*)2:NULL;*x=512;*y=448;return acquireOK;
}
bool SDL_SubmitGPUCommandBuffer(SDL_GPUCommandBuffer *c) {(void)c;return submitOK;}
SDL_GPUTexture *DrOptical_Image(DrOptical *f,SDL_GPUCommandBuffer *c,float a,int h) {
 (void)f;(void)c;(void)h;assert(a>0 && a<1);flowImage++;return (SDL_GPUTexture*)3;
}
Uint32 DrOptical_Width(const DrOptical *f) {(void)f;return 512;}
Uint32 DrOptical_Height(const DrOptical *f) {(void)f;return 448;}
void DrOptical_Reset(DrOptical *f) {(void)f;resets++;}
static void show_target(SDL_GPUCommandBuffer *c,int best,SDL_GPUTexture *t,Uint32 w,Uint32 h) {
 (void)c;(void)t;(void)w;(void)h;assert(best==0);realImage++;
}
static void show_image(SDL_GPUCommandBuffer *c,SDL_GPUTexture *src,int tw,int th,int iw,int ih,SDL_GPUTexture *dst,Uint32 sw,Uint32 sh) {
 (void)c;(void)src;(void)tw;(void)th;(void)iw;(void)ih;(void)dst;(void)sw;(void)sh;
}
void Ui_Draw(SDL_GPUCommandBuffer *c,SDL_GPUTexture *t) {(void)c;(void)t;liveUI++;nextDrawCount=0;}
void Ui_DrawAgain(SDL_GPUCommandBuffer *c,SDL_GPUTexture *t) {(void)c;(void)t;cachedUI++;}
'''
main=r'''
int main(void) {
 for(int n=2;n<=4;n++)for(int k=2;k<=n;k++) {
  assert(GsVkOptical_Present(k,n)==(k==n?'R':'B'));
  assert(!liveUI && nextDrawCount==17);
 }
 assert(events==6 && cachedUI==6 && realImage==3 && flowImage==3);
 acquireOK=0;assert(!GsVkOptical_Present(2,2));assert(cachedUI==6);
 acquireOK=1;submitOK=0;assert(!GsVkOptical_Present(2,2));assert(!sOptPair && resets==1);
 sOptPair=1;submitOK=1;commandOK=0;assert(!GsVkOptical_Present(2,2));
 assert(nextDrawCount==17 && !liveUI);
 puts("PASS production optical present: real/generated kinds, cached UI, preserved next list, acquire/submit failures");
}
'''
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp);(p/'test.c').write_text(prefix+s[start:i]+main)
 subprocess.run(['cc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
                 '-I'+sys.argv[2],'-I'+str(root/'port/src/gs'),str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0'})
