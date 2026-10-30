#!/usr/bin/env python3
"""Real Vulkan + production optical presenter, optionally with an X11 swapchain.
No ROM/game/device performance assertions; these are synthetic pixel scenes."""
from pathlib import Path
import os,re,subprocess,sys,tempfile
root=Path(sys.argv[1]).resolve();tests=Path(__file__).resolve().parent
s=(root/'port/src/gs/gs_gpu.c').read_text()
m=re.search(r'^int GsVkOptical_Present\([^;]*?\)\s*\{',s,re.M);assert m
start=m.start();end=s.index('{',start)+1;depth=1
while depth:depth+=(s[end]=='{')-(s[end]=='}');end+=1
draw=(root/'port/src/gs/gs_draw.c').read_text()
def extract(name):
 m=re.search(r'^static (?:int|void) '+name+r'\([^;]*?\)\s*\{',draw,re.M);assert m,name
 end=draw.index('{',m.start())+1;depth=1
 while depth:depth+=(draw[end]=='{')-(draw[end]=='}');end+=1
 return draw[m.start():end]
planner='\n'.join(extract(n) for n in ('interp_steps','interp_select_steps'))
prefix=r''' 
#define main optical_reference_main
#include "optical_gpu_test.c"
#undef main
#include "gs_fg_probe.h"
#include "gs_fg_trace.h"
#include "gs_perf.h"
#define MAX_TARGETS 3
#define SCALE 1
#define sDev dev
static SDL_Window *sWindow;
static DrOptical *sOptical;
static SDL_GPUTexture *sTgCol[3];
static int sOptPair=1,sLastShown=0,sTW=512,sTH=448;
static uint64_t sFgSource,sFgPrevious,sFgEpoch;
static int windowed;
static DrOpticalCadence sOpticalCadence;
static uint64_t sOpticalCadenceEpoch,sInterpTickNs;
static unsigned sInterpLastBlank,blank;
static int gsInterp=2,sInterpCap=4,sInterpSteps,gPortInMenus;
unsigned Gs_RenderBlank(void){return blank;}
uint64_t Gs_RenderEpoch(void){return GsFg_Epoch();}
unsigned long long Port_BlankNs(void){return 16683350ull*100/114;}
unsigned long long gPortSleptNs;
int Gs_RenderThreaded(void){return 0;}
int Port_Setting(const char *k,int d){(void)k;return d;}
static int window_ready(void){return sWindow!=NULL;}
static void poll_events(void){SDL_Event e;while(SDL_PollEvent(&e)){} }
static void present_apply(void){}
int GsVkOptical_EpochValid(void){return sFgEpoch==GsFg_Epoch();}
void GsVkOptical_DropRange(int a,int b,int why){for(int k=a;k<=b;k++)GsFg_Event(FG_DROP,sFgSource|(uint64_t)k,why,0);}
void GsVkOptical_Reset(int r){(void)r;sOptPair=0;DrOptical_Reset(sOptical);}
static void show_image(SDL_GPUCommandBuffer *cmd,SDL_GPUTexture *image,int tw,int th,int iw,int ih,SDL_GPUTexture *swap,Uint32 sw,Uint32 sh) {
 (void)tw;(void)th;SDL_GPUBlitInfo bl;SDL_zero(bl);
 bl.source.texture=image;bl.source.w=(Uint32)iw;bl.source.h=(Uint32)ih;
 bl.destination.texture=swap;bl.destination.w=sw;bl.destination.h=sh;
 bl.load_op=SDL_GPU_LOADOP_DONT_CARE;bl.filter=SDL_GPU_FILTER_LINEAR;SDL_BlitGPUTexture(cmd,&bl);
}
static void show_target(SDL_GPUCommandBuffer *cmd,int best,SDL_GPUTexture *swap,Uint32 w,Uint32 h){show_image(cmd,sTgCol[best],W,H,W,H,swap,w,h);}
void Ui_DrawAgain(SDL_GPUCommandBuffer *c,SDL_GPUTexture *t){(void)c;(void)t;}
'''
main=r'''
static int capture(double shift,int steps) {
 unsigned char *px=malloc(BYTES);check(px!=NULL,"pixels");scene(px,shift);upload(sTgCol[0],px);free(px);
 sFgPrevious=sFgSource;sFgSource=GsFg_Source(SDL_GetTicksNS(),(unsigned)(shift*2));sFgEpoch=GsFg_Epoch();
 GsFg_Register(sFgSource|7,sFgPrevious,sFgSource,FG_FLOW,0);
 SDL_GPUCommandBuffer *c=SDL_AcquireGPUCommandBuffer(dev);
 GsFg_Compute(sFgSource|7,DR_VK_FLOW);
 int pair=DrOptical_Capture(sOptical,c,sTgCol[0],W,H,steps>1);GsFg_Compute(0,0);
 if(pair)GsFg_Event(FG_DISPATCH,sFgSource|7,0,0);
 check(GsFg_Submit(c,0,sFgSource),"capture submit");
 check(SDL_WaitForGPUIdle(dev),"capture fence");sOptPair=pair>0;
 for(int k=1;k<steps;k++)GsFg_Register(sFgSource|(uint64_t)k,sFgPrevious,sFgSource,FG_GENERATED,0);
 return pair;
}
static void headless(int step,int steps) {
 uint64_t id=step==steps?sFgSource:sFgSource|(uint64_t)step;
 SDL_GPUCommandBuffer *c=SDL_AcquireGPUCommandBuffer(dev);
 SDL_GPUTexture *image=sTgCol[0];Uint32 w=W,h=H;
 if(step<steps) {
  GsFg_Event(FG_DEQUEUE,id,step,steps);GsFg_Event(FG_DISPATCH,id,step,steps);GsFg_Compute(id,DR_VK_SYNTH);
  image=DrOptical_Image(sOptical,c,(float)step/steps,0);GsFg_Compute(0,0);
  w=DrOptical_Width(sOptical);h=DrOptical_Height(sOptical);
 }
 GsFg_Verify(c,image,w,h,w,h,id,step<steps,DrOptical_Scene(sOptical));
 check(GsFg_Submit(c,0,0),"headless submit");check(SDL_WaitForGPUIdle(dev),"complete fence");
}
static void native_present(void) {
 SDL_GPUCommandBuffer *c=SDL_AcquireGPUCommandBuffer(dev);SDL_GPUTexture *swap=NULL;Uint32 sw=0,sh=0;
 check(SDL_WaitAndAcquireGPUSwapchainTexture(c,sWindow,&swap,&sw,&sh) && swap,"native swapchain");
 show_target(c,0,swap,sw,sh);GsFg_Verify(c,sTgCol[0],W,H,W,H,sFgSource,0,NULL);
 GsFg_Event(FG_COMPOSITE,sFgSource,'S',0);check(GsFg_Submit(c,sFgSource,0),"native present");
 check(SDL_WaitForGPUIdle(dev),"native fence");
}
int main(int argc,char **argv) {
 (void)argv;setvbuf(stdout,NULL,_IOLBF,0);windowed=argc>1;
 check(SDL_Init(SDL_INIT_VIDEO),"video");SDL_PropertiesID p=SDL_CreateProperties();
 GsFg_DeviceProperties(p);SDL_SetBooleanProperty(p,SDL_PROP_GPU_DEVICE_CREATE_SHADERS_SPIRV_BOOLEAN,true);
 SDL_SetBooleanProperty(p,SDL_PROP_GPU_DEVICE_CREATE_DEBUGMODE_BOOLEAN,true);
 dev=SDL_CreateGPUDeviceWithProperties(p);SDL_DestroyProperties(p);check(dev!=NULL,"device");GsFg_Device(dev);
 sOptical=DrOptical_Create(dev,0);check(sOptical!=NULL,"optical graph");sTgCol[0]=image();
 GsPerf_FramegenSet(4,4,DR_FG_ACTIVE);GsPerf_SetRefreshMilliHz(120000);
 if(windowed){sWindow=SDL_CreateWindow("Dragon Rage pipeline test",512,448,0);check(sWindow!=NULL,"window");check(SDL_ClaimWindowForGPUDevice(dev,sWindow),"swapchain");check(SDL_SetGPUSwapchainParameters(dev,sWindow,SDL_GPU_SWAPCHAINCOMPOSITION_SDR,SDL_GPU_PRESENTMODE_VSYNC),"FIFO");}
 /* Reference, FG off: render/capture completes; no generated frame. */
 assert(capture(0,1)==0);GsFgStats stats;GsFg_Snapshot(&stats);assert(stats.real==1 && !stats.completed && !stats.presented);
 headless(1,1); /* establish the proof's previous submitted GPU image */
 unsigned expected=0,presents=0;
 for(int n=2;n<=4;n++) {
  assert(capture((double)(n-1)*12,n)==1);
  for(int k=1;k<=n;k++) {
   if(windowed){assert(GsVkOptical_Present(k,n)==(k==n?'R':'B'));presents++;check(SDL_WaitForGPUIdle(dev),"present fence");}
   else headless(k,n);
  }
  expected+=(unsigned)n-1;GsFg_Snapshot(&stats);
  assert(stats.completed==expected && stats.presented==presents);
  if(windowed)assert(stats.generatedPresented==expected);
  else assert(!stats.generatedPresented && !stats.displayed);
  printf("PASS real Vulkan %dx: complete=%llu present_ok=%llu FG_unique_present_ok=%llu display_feedback=%llu gpu_flow_ns=%llu gpu_synth_ns=%llu\n",n,(unsigned long long)stats.completed,(unsigned long long)stats.presented,(unsigned long long)stats.generatedPresented,(unsigned long long)stats.displayed,(unsigned long long)stats.flowGpuNs,(unsigned long long)stats.synthGpuNs);
 }
 assert(stats.observer && stats.gpuTimer && stats.flowGpuNs>0 && stats.synthGpuNs>0);
 /* Reproduce the device's actual 114%/60 Hz plan through real compute,
    proof, fences and the production optical presenter. This is synthetic
    content, not an online gameplay/phone performance benchmark. */
 GsPerf_SetRefreshMilliHz(60000);unsigned replayGen=0,replayOld=0;
 for(int i=0;i<12;i++) {
  blank+=2;interp_select_steps(1);int n=sInterpSteps;
  int pair=capture(48+(double)i*6,n);assert((n>1)==(pair>0));
  GsFg_Event(FG_PLAN,sFgSource,n,60000);GsFg_Event(FG_PAIR,sFgSource,pair,n);
  replayOld+=(unsigned)DrTickDisplaySteps(2,60000,2*Port_BlankNs())-1;
  for(int k=1;k<=n;k++) {
   if(windowed){if(n==1)native_present();else {assert(GsVkOptical_Present(k,n)==(k==n?'R':'B'));check(SDL_WaitForGPUIdle(dev),"replay fence");}presents++;}
   else headless(k,n);
  }
  expected+=(unsigned)n-1;replayGen+=(unsigned)n-1;
 }
 GsFg_Snapshot(&stats);assert(stats.completed==expected && !replayOld && replayGen==9);
 assert(stats.presented==presents);
 if(windowed)assert(stats.generatedPresented==expected);
 printf("PASS actual Vulkan device-case 114%%/60Hz: 12 sources, 9 temporal images, complete=%llu FG_unique_present_ok=%llu raw_present=%llu; old policy=0\n",(unsigned long long)stats.completed,(unsigned long long)stats.generatedPresented,(unsigned long long)stats.presented);
 /* Visible epoch changes invalidate a pending extra without changing a pixel
    of simulation/network state. Presenter must not submit it after rollback. */
 if(windowed){GsFg_Rollback(8);assert(!GsVkOptical_Present(2,4));GsFg_Snapshot(&stats);assert(stats.presented==presents);}
 /* Static proof must not count a repeated source as unique. */
 uint64_t unique=stats.uniquePresented;
 sFgSource=GsFg_Source(SDL_GetTicksNS(),100);headless(1,1);GsFg_Snapshot(&stats);assert(stats.uniquePresented==unique);
 GsFg_Flush();SDL_Delay(100); /* bounded evidence writer, not a measured frame */
 check(SDL_WaitForGPUIdle(dev),"final wait");DrOptical_Destroy(sOptical);
 SDL_ReleaseGPUTexture(dev,sTgCol[0]);GsFg_Device(NULL);
 if(sWindow){SDL_ReleaseWindowFromGPUDevice(dev,sWindow);SDL_DestroyWindow(sWindow);}
 SDL_DestroyGPUDevice(dev);SDL_Quit();
 puts("PASS GPU fence/queries/proof ledger; headless computation never claims presentation; swapchain mode uses actual VkResult");
 return 0;
}
'''
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp);(p/'test.c').write_text(prefix+planner+s[start:end]+main)
 sources=[p/'test.c',root/'port/src/gs/gs_optical.c',root/'port/src/gs/gs_fg_probe.c',root/'port/src/gs/gs_fg_trace.c',root/'port/src/gs/gs_perf.c']
 cmd=['cc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-fsanitize=address,undefined','-fno-omit-frame-pointer',
  '-I'+str(tests),'-I'+os.environ['DR_FG_SDL_INCLUDE'],'-I'+os.environ['DR_FG_TEST_GEN'],'-I'+str(root/'port/src/gs'),*map(str,sources),
  '-L'+os.environ['DR_FG_SDL_ROOT'],'-Wl,-rpath,'+os.environ['DR_FG_SDL_ROOT'],'-lSDL3','-lm','-pthread','-o',str(p/'test')]
 subprocess.run(cmd,check=True)
 subprocess.run([str(p/'test')]+sys.argv[2:],check=True,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0'})
