#include <SDL3/SDL.h>
#include <stdlib.h>
#include <assert.h>
#include <stdio.h>
static int failHost,failNth,attempts,live,unsupported;
static void *host_calloc(size_t n,size_t size) { return failHost ? NULL : calloc(n,size); }
#define calloc host_calloc
#include "gs_optical.c"
#undef calloc
static void *resource(void) {
    if (++attempts==failNth) return NULL;
    void *p=malloc(1);assert(p);live++;return p;
}
bool SDL_SetError(const char *format,...) { (void)format;return false; }
bool SDL_OutOfMemory(void) { return false; }
bool SDL_GPUTextureSupportsFormat(SDL_GPUDevice *d,SDL_GPUTextureFormat f,SDL_GPUTextureType t,SDL_GPUTextureUsageFlags u) {
    (void)d;(void)f;(void)t;(void)u;return !unsupported;
}
SDL_GPUTexture *SDL_CreateGPUTexture(SDL_GPUDevice *d,const SDL_GPUTextureCreateInfo *i) {
    (void)d;(void)i;return resource();
}
SDL_GPUSampler *SDL_CreateGPUSampler(SDL_GPUDevice *d,const SDL_GPUSamplerCreateInfo *i) {
    (void)d;(void)i;return resource();
}
SDL_GPUComputePipeline *SDL_CreateGPUComputePipeline(SDL_GPUDevice *d,const SDL_GPUComputePipelineCreateInfo *i) {
    (void)d;(void)i;return resource();
}
void SDL_ReleaseGPUTexture(SDL_GPUDevice *d,SDL_GPUTexture *p) { (void)d;assert(p);live--;free(p); }
void SDL_ReleaseGPUSampler(SDL_GPUDevice *d,SDL_GPUSampler *p) { (void)d;assert(p);live--;free(p); }
void SDL_ReleaseGPUComputePipeline(SDL_GPUDevice *d,SDL_GPUComputePipeline *p) { (void)d;assert(p);live--;free(p); }
int main(void) {
    DrOptical *f=DrOptical_Create((SDL_GPUDevice*)1,1);assert(f);int total=attempts;
    DrOptical_Destroy(f);assert(live==0 && total>20);
    for(int i=1;i<=total;i++) {
        attempts=0;failNth=i;f=DrOptical_Create((SDL_GPUDevice*)1,1);
        assert(f==NULL && live==0);
    }
    failNth=0;attempts=0;failHost=1;assert(DrOptical_Create((SDL_GPUDevice*)1,1)==NULL && live==0 && attempts==0);
    failHost=0;unsupported=1;assert(DrOptical_Create((SDL_GPUDevice*)1,1)==NULL && live==0);
    printf("PASS production optical init cleanup: all %d resource failure sites, host allocation failure, unsupported format\n",total);
}
