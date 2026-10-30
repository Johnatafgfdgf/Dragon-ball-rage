#!/usr/bin/env python3
"""Compile production resim dispatch; assert GS decode never changes owner."""
from pathlib import Path
import re,subprocess,tempfile,os,sys
root=Path(sys.argv[1]);s=(root/'port/src/gs/gs_core.c').read_text()
m=re.search(r'^static int resim_chain\([^;]*?\)\s*\{',s,re.M);assert m
i=s.index('{',m.start())+1;depth=1
while depth:depth+=(s[i]=='{')-(s[i]=='}');i+=1
prefix=r'''
#include <assert.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
static int gPortResim,sGpu,sThreaded,enabled=1,ticks,decoded,posted,waits,busy;
static pthread_t mainThread,worker;
static size_t sFrozenUsed;
static void run_chain(uint32_t a,int b){(void)a;(void)b;assert(!sThreaded && pthread_equal(pthread_self(),mainThread));decoded++;}
static void freeze_block(const uint32_t *a,const uint32_t *b,uint32_t c,int d){(void)a;(void)b;(void)c;(void)d;}
static void walk_chain(uint32_t a,int b,void (*cb)(const uint32_t*,const uint32_t*,uint32_t,int)){(void)a;(void)b;(void)cb;assert(sThreaded && pthread_equal(pthread_self(),mainThread));assert(!sFrozenUsed);}
static void *work(void *arg){(void)arg;assert(!pthread_equal(pthread_self(),mainThread) && gPortResim);decoded++;return NULL;}
static void render_wait(void){waits++;if(busy){pthread_join(worker,NULL);busy=0;}}
static void render_post(int job,uint32_t a,int b){(void)a;(void)b;assert(job==2 && gPortResim);posted++;busy=1;assert(!pthread_create(&worker,NULL,work,NULL));}
void GsGpu_InterpHurry(int on){assert(on==1);}
static int gs_on(void){return enabled;}
void GsFg_ResimTick(void){ticks++;}
'''
main=r'''
int main(void){
 mainThread=pthread_self();assert(!resim_chain(1,0) && !ticks && !decoded);
 gPortResim=1;enabled=0;assert(resim_chain(1,0) && ticks==1 && !decoded);
 enabled=1;assert(resim_chain(1,0) && ticks==2 && decoded==1);
 sGpu=1;assert(resim_chain(1,0) && ticks==3 && decoded==2);
 sThreaded=1;sFrozenUsed=123;assert(resim_chain(1,0));
 assert(!busy && posted==1 && waits==2 && decoded==3 && ticks==4 && gPortResim==1);
 gPortResim=0;assert(!resim_chain(1,0) && decoded==3);
 puts("PASS production resim DMA dispatch: owner-thread decode, frozen handoff, replay lifetime, no visual tick or network state changes");
}
'''
assert s.index('if(resim_chain(tadr,tte))return;')<s.index('unsigned blanks = gPortVBlanks - lastBlank;')
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp);(p/'test.c').write_text(prefix+s[m.start():i]+main)
 subprocess.run(['cc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-pthread','-fsanitize=address,undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0'})
