/* Executes the production C graph and actual SPIR-V on a Vulkan GPU (CI: lavapipe).
   Synthetic motion gives a known intermediate image, unlike a shader-only test. */
#include "gs_optical.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define W 512
#define H 448
#define BYTES (W*H*4)
static SDL_GPUDevice *dev;
static void check(int ok,const char *what) {
    if (!ok) { fprintf(stderr,"%s: %s\n",what,SDL_GetError()); exit(1); }
}
static void finish(SDL_GPUCommandBuffer *cmd) {
    SDL_GPUFence *f=SDL_SubmitGPUCommandBufferAndAcquireFence(cmd);
    check(f!=NULL,"submit"); check(SDL_WaitForGPUFences(dev,true,&f,1),"wait");
    SDL_ReleaseGPUFence(dev,f);
}
static SDL_GPUTexture *image(void) {
    SDL_GPUTextureCreateInfo c;
    SDL_zero(c); c.type=SDL_GPU_TEXTURETYPE_2D; c.format=SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM;
    c.usage=SDL_GPU_TEXTUREUSAGE_SAMPLER|SDL_GPU_TEXTUREUSAGE_COLOR_TARGET;
    c.width=W;c.height=H;c.layer_count_or_depth=c.num_levels=1;
    SDL_GPUTexture *t=SDL_CreateGPUTexture(dev,&c);check(t!=NULL,"image");return t;
}
static void upload(SDL_GPUTexture *t,const unsigned char *pixels) {
    SDL_GPUTransferBufferCreateInfo c={SDL_GPU_TRANSFERBUFFERUSAGE_UPLOAD,BYTES,0};
    SDL_GPUTransferBuffer *tb=SDL_CreateGPUTransferBuffer(dev,&c);check(tb!=NULL,"upload buffer");
    void *map=SDL_MapGPUTransferBuffer(dev,tb,false);check(map!=NULL,"map upload");
    memcpy(map,pixels,BYTES);SDL_UnmapGPUTransferBuffer(dev,tb);
    SDL_GPUCommandBuffer *cmd=SDL_AcquireGPUCommandBuffer(dev);
    SDL_GPUCopyPass *cp=SDL_BeginGPUCopyPass(cmd);
    SDL_GPUTextureTransferInfo src;SDL_zero(src);src.transfer_buffer=tb;
    SDL_GPUTextureRegion dst;SDL_zero(dst);dst.texture=t;dst.w=W;dst.h=H;dst.d=1;
    SDL_UploadToGPUTexture(cp,&src,&dst,false);SDL_EndGPUCopyPass(cp);finish(cmd);
    SDL_ReleaseGPUTransferBuffer(dev,tb);
}
static void download(SDL_GPUCommandBuffer *cmd,SDL_GPUTexture *t,unsigned char *pixels) {
    SDL_GPUTransferBufferCreateInfo c={SDL_GPU_TRANSFERBUFFERUSAGE_DOWNLOAD,BYTES,0};
    SDL_GPUTransferBuffer *tb=SDL_CreateGPUTransferBuffer(dev,&c);check(tb!=NULL,"download buffer");
    SDL_GPUCopyPass *cp=SDL_BeginGPUCopyPass(cmd);
    SDL_GPUTextureRegion src;SDL_zero(src);src.texture=t;src.w=W;src.h=H;src.d=1;
    SDL_GPUTextureTransferInfo dst;SDL_zero(dst);dst.transfer_buffer=tb;
    SDL_DownloadFromGPUTexture(cp,&src,&dst);SDL_EndGPUCopyPass(cp);finish(cmd);
    void *map=SDL_MapGPUTransferBuffer(dev,tb,false);check(map!=NULL,"map download");
    memcpy(pixels,map,BYTES);SDL_UnmapGPUTransferBuffer(dev,tb);SDL_ReleaseGPUTransferBuffer(dev,tb);
}
static double pattern(double x,double y,int channel) {
    double v=0.5+0.16*sin(x*0.117+y*0.073+channel)+0.13*cos(x*0.041-y*0.151+channel*2)
                 +0.11*sin(x*0.331+y*0.251)+0.07*cos(x*0.53-y*0.411);
    return fmin(1,fmax(0,v));
}
static void scene(unsigned char *p,double shift) {
    for(int y=0;y<H;y++)for(int x=0;x<W;x++) {
        for(int c=0;c<3;c++)p[4*(y*W+x)+c]=(unsigned char)lround(pattern(x-shift,y,c)*255);
        p[4*(y*W+x)+3]=255;
    }
}
static double error(const unsigned char *p,const unsigned char *truth) {
    double sum=0;unsigned n=0;
    for(int y=32;y<H-32;y++)for(int x=48;x<W-48;x++)for(int c=0;c<3;c++) {
        double d=(double)p[4*(y*W+x)+c]-truth[4*(y*W+x)+c];sum+=d*d;n++;
    }
    return sum/n;
}
int main(void) {
    setvbuf(stdout,NULL,_IOLBF,0);
    check(SDL_Init(SDL_INIT_VIDEO),"SDL video");
    dev=SDL_CreateGPUDevice(SDL_GPU_SHADERFORMAT_SPIRV,true,"vulkan");check(dev!=NULL,"Vulkan device");
    DrOptical *fg=DrOptical_Create(dev,1);check(fg!=NULL,"production graph");
    printf("optical GPU images: %.3f MiB\n",(double)DrOptical_Bytes(fg)/1048576.0);
    assert(DrOptical_Bytes(fg)<6*1024*1024);
    SDL_GPUTexture *src=image();
    unsigned char *a=malloc(BYTES),*b=malloc(BYTES),*out=malloc(BYTES),*truth=malloc(BYTES),*blend=malloc(BYTES);
    check(a&&b&&out&&truth&&blend,"host pixels");
    scene(a,0);scene(b,12);
    upload(src,a);
    SDL_GPUCommandBuffer *cmd=SDL_AcquireGPUCommandBuffer(dev);
    assert(DrOptical_Capture(fg,cmd,src,W,H,1)==0);finish(cmd);
    upload(src,b);cmd=SDL_AcquireGPUCommandBuffer(dev);
    assert(DrOptical_Capture(fg,cmd,src,W,H,1)==1);finish(cmd);
    double worst=0;
    for(int multiplier=2;multiplier<=4;multiplier++)for(int k=1;k<multiplier;k++) {
        float alpha=(float)k/(float)multiplier;
        cmd=SDL_AcquireGPUCommandBuffer(dev);
        SDL_GPUTexture *result=DrOptical_Image(fg,cmd,alpha,0);check(result!=NULL,"synthesis");download(cmd,result,out);
        scene(truth,12*alpha);
        for(int i=0;i<BYTES;i++)blend[i]=(unsigned char)lround(a[i]*(1-alpha)+b[i]*alpha);
        double mse=error(out,truth),baseline=error(blend,truth),ratio=mse/baseline;
        printf("%dx alpha %.4f: optical MSE %.3f, blend MSE %.3f, ratio %.3f\n",multiplier,alpha,mse,baseline,ratio);
        if(ratio>worst)worst=ratio;
        assert(ratio<0.70); /* A cross-fade or repeated real frame cannot pass. */
    }
    cmd=SDL_AcquireGPUCommandBuffer(dev);download(cmd,DrOptical_Image(fg,cmd,1,0),out);
    assert(memcmp(out,b,BYTES)==0);
    cmd=SDL_AcquireGPUCommandBuffer(dev);download(cmd,DrOptical_Image(fg,cmd,0.5f,1),out);
    assert(memcmp(out,b,W*(int)(H*0.18f)*4)==0);
    /* Extra diagnostic: two independently moving textured regions. */
    DrOptical_Reset(fg);
    for(int y=0;y<H;y++)for(int x=0;x<W;x++)for(int c=0;c<4;c++) {
        int i=4*(y*W+x)+c;
        if(c==3) { a[i]=b[i]=truth[i]=255;continue; }
        double motion=x<W/2?12:-8;
        a[i]=(unsigned char)lround(pattern(x,y,c+(x>=W/2))*255);
        b[i]=(unsigned char)lround(pattern(x-motion,y,c+(x>=W/2))*255);
        truth[i]=(unsigned char)lround(pattern(x-motion/2,y,c+(x>=W/2))*255);
    }
    upload(src,a);cmd=SDL_AcquireGPUCommandBuffer(dev);assert(DrOptical_Capture(fg,cmd,src,W,H,1)==0);finish(cmd);
    upload(src,b);cmd=SDL_AcquireGPUCommandBuffer(dev);assert(DrOptical_Capture(fg,cmd,src,W,H,1)==1);
    download(cmd,DrOptical_Image(fg,cmd,0.5f,0),out);
    double multi=0,base=0;unsigned count=0;
    for(int y=32;y<H-32;y++)for(int x=48;x<W-48;x++)if(abs(x-W/2)>48)for(int c=0;c<3;c++) {
        int i=4*(y*W+x)+c;double d=(double)out[i]-truth[i],bd=0.5*(a[i]+b[i])-truth[i];
        multi+=d*d;base+=bd*bd;count++;
    }
    printf("extra independent motion: optical MSE %.3f, blend MSE %.3f, ratio %.5f\n",multi/count,base/count,multi/base);
    assert(multi<base*0.7);
    /* Restore original scene for the remaining static test. */
    scene(b,12);upload(src,b);DrOptical_Reset(fg);cmd=SDL_AcquireGPUCommandBuffer(dev);
    assert(DrOptical_Capture(fg,cmd,src,W,H,1)==0);finish(cmd);
    /* Identical images must not acquire temporal drift. */
    cmd=SDL_AcquireGPUCommandBuffer(dev);assert(DrOptical_Capture(fg,cmd,src,W,H,1)==1);
    download(cmd,DrOptical_Image(fg,cmd,0.5f,0),out);
    assert(error(out,b)<0.1);
    /* A hard luminance cut produces current pixels, with no double exposure. */
    memset(a,0,BYTES);for(int i=3;i<BYTES;i+=4)a[i]=255;
    memset(b,255,BYTES);
    DrOptical_Reset(fg);upload(src,a);cmd=SDL_AcquireGPUCommandBuffer(dev);
    assert(DrOptical_Capture(fg,cmd,src,W,H,1)==0);finish(cmd);
    upload(src,b);cmd=SDL_AcquireGPUCommandBuffer(dev);assert(DrOptical_Capture(fg,cmd,src,W,H,1)==1);
    download(cmd,DrOptical_Image(fg,cmd,0.5f,0),out);assert(memcmp(out,b,BYTES)==0);
    /* Disabled generation, history invalidation and re-warmup. */
    cmd=SDL_AcquireGPUCommandBuffer(dev);assert(DrOptical_Capture(fg,cmd,src,W,H,0)==0);finish(cmd);
    DrOptical_Reset(fg);cmd=SDL_AcquireGPUCommandBuffer(dev);assert(DrOptical_Capture(fg,cmd,src,W,H,1)==0);finish(cmd);
    DrOptical_Destroy(fg);
    for(int q=0;q<=2;q+=2) {
        fg=DrOptical_Create(dev,q);check(fg!=NULL,"quality allocation");
        scene(a,0);scene(b,12);upload(src,a);cmd=SDL_AcquireGPUCommandBuffer(dev);
        assert(DrOptical_Capture(fg,cmd,src,W,H,1)==0);finish(cmd);
        upload(src,b);cmd=SDL_AcquireGPUCommandBuffer(dev);
        assert(DrOptical_Capture(fg,cmd,src,W,H,1)==1);
        SDL_GPUTexture *result=DrOptical_Image(fg,cmd,0.5f,0);check(result!=NULL,"quality synthesis");
        SDL_GPUTexture *scaled=image();SDL_GPUBlitInfo bl;SDL_zero(bl);
        bl.source.texture=result;bl.source.w=DrOptical_Width(fg);bl.source.h=DrOptical_Height(fg);
        bl.destination.texture=scaled;bl.destination.w=W;bl.destination.h=H;
        bl.filter=SDL_GPU_FILTER_LINEAR;bl.load_op=SDL_GPU_LOADOP_DONT_CARE;
        SDL_BlitGPUTexture(cmd,&bl);download(cmd,scaled,out);
        scene(truth,6);double mse=error(out,truth);
        printf("quality %d, %ux%u, %.3f MiB: midpoint MSE %.3f\n",q,DrOptical_Width(fg),DrOptical_Height(fg),
               (double)DrOptical_Bytes(fg)/1048576.0,mse);
        assert(mse<100);
        SDL_ReleaseGPUTexture(dev,scaled);DrOptical_Destroy(fg);
    }
    SDL_ReleaseGPUTexture(dev,src);check(SDL_WaitForGPUIdle(dev),"idle");SDL_DestroyGPUDevice(dev);SDL_Quit();
    free(a);free(b);free(out);free(truth);free(blend);
    printf("PASS optical motion 2x/3x/4x, real endpoint, HUD, static, scene cut, reset; worst ratio %.3f\n",worst);
    return 0;
}
