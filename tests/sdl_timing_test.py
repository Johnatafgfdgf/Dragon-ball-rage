#!/usr/bin/env python3
"""Compile the patched vendor's actual timing/present blocks against Vulkan headers.
The extension is unavailable in lavapipe; this fault-injection test exercises its
call contract, not physical display timing or a real Android driver.
"""
from pathlib import Path
import os,re,subprocess,sys,tempfile
root=Path(sys.argv[1]);sdl=Path(sys.argv[2]);s=(sdl/'src/gpu/vulkan/SDL_gpu_vulkan.c').read_text()
m=re.search(r'^static void DR_VkPast\([^;]*?\)\s*\{',s,re.M);assert m
end=s.index('{',m.start())+1;depth=1
while depth:depth+=(s[end]=='{')-(s[end]=='}');end+=1
past=s[m.start():end]
start=s.index('        Uint64 drImage=renderer->drProbe?renderer->drProbe->image:0;')
end=s.index('        presentResult = renderer->vkQueuePresentKHR(',start)
block=s[start:end]
prefix=r'''
#include <assert.h>
#include <stdio.h>
#include <SDL3/SDL_stdinc.h>
#include <vulkan/vulkan.h>
#include "dr_vk_probe.h"
typedef struct VulkanRenderer {
 DrVkProbe *drProbe;
 PFN_vkGetPastPresentationTimingGOOGLE drPastTiming;
 VkDevice logicalDevice;Uint32 drPresentSerial;
 struct { VkSwapchainKHR swap;Uint32 serial;Uint64 id;} drPresents[512];
} VulkanRenderer;
typedef struct {struct {VkSwapchainKHR swapchain;} *windowData;} PresentData;
static int nullQueries,filledQueries,events,available;
static Uint32 pendingID;
static VkSwapchainKHR swap=(VkSwapchainKHR)(uintptr_t)123;
static void DR_VkEvent(VulkanRenderer *r,int what,Uint64 id,Sint64 time,Uint64 detail){
 (void)r;(void)detail;assert(what==DR_VK_DISPLAY || what==DR_VK_RETIRED);
 if(what==DR_VK_DISPLAY){assert(id==17 && time==1000000016666667ll);events++;}
}
static VKAPI_ATTR VkResult VKAPI_CALL fakePast(VkDevice dev,VkSwapchainKHR chain,uint32_t *count,VkPastPresentationTimingGOOGLE *out){
 (void)dev;assert(chain==swap);
 if(!out){nullQueries++;*count=(uint32_t)available;return VK_SUCCESS;}
 filledQueries++;assert(*count>0 && *count<=64);
 out[0]=(VkPastPresentationTimingGOOGLE){.presentID=pendingID,.actualPresentTime=1000000016666667ull};
 *count=1;available=0;return VK_SUCCESS;
}
'''
main=r'''
 if(renderer->drPastTiming && renderer->drProbe && renderer->drProbe->image){
  const VkPresentTimesInfoGOOGLE *times=presentInfo.pNext;assert(times && times->swapchainCount==1);
  assert(times->pTimes[0].desiredPresentTime==renderer->drProbe->desiredPresentNs);
  assert(times->pTimes[0].presentID==renderer->drPresentSerial);
 }else assert(presentInfo.pNext==NULL);
}
int main(void){
 DrVkProbe probe={.abi=DR_VK_PROBE_ABI,.image=17,.desiredPresentNs=1000000000000000ull};
 VulkanRenderer r={.drProbe=&probe,.drPastTiming=fakePast};
 struct {VkSwapchainKHR swapchain;} window={swap};
 PresentData data;data.windowData=(void*)&window;
 actualPresentBlock(&r,&data);assert(nullQueries==1 && !filledQueries);
 pendingID=r.drPresentSerial;available=1;probe.image=24;probe.desiredPresentNs+=16666667;
 actualPresentBlock(&r,&data);assert(nullQueries==2 && filledQueries==1 && events==1);
 r.drPastTiming=NULL;actualPresentBlock(&r,&data);assert(nullQueries==2);
 r.drProbe=NULL;actualPresentBlock(&r,&data);assert(nullQueries==2);
 puts("PASS actual SDL Vulkan timing blocks: absolute timestamp forwarded, count-first feedback query, matching image ID, unsupported/unobserved fallback");
}
'''
with tempfile.TemporaryDirectory() as tmp:
    p=Path(tmp);(p/'test.c').write_text(prefix+past+'\nstatic void actualPresentBlock(VulkanRenderer *renderer,PresentData *presentData){\n VkPresentInfoKHR presentInfo={0};\n'+block+main)
    subprocess.run(['cc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
        '-I'+str(sdl/'include'),'-I'+str(sdl/'src/video/khronos'),'-I'+str(root/'port/src/gs'),str(p/'test.c'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0'})
