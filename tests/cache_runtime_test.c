/* Exercise the actual production cache using pthread-backed SDL synchronisation.
   Fake DDS inputs go through its real loader, decompressor, queue and eviction. */
#include <assert.h>
#include <stdio.h>
#include <unistd.h>
#include <string.h>
#include <time.h>
#include <SDL3/SDL.h>
#include "gs_perf.h"
#include "gs_texpack.c"
#undef getenv
const char *Port_GetEnv(const char *name) { return getenv(name); }
int gGsNoBcTextures=1, gGsAstcTextures=0;
int Port_Setting(const char *key,int def) { (void)key; return def; }
int GsAstc_Load(const char *path,TexPackImage *img) { (void)path;(void)img; return 0; }
void GsAstc_Queue(const char *path) { (void)path; }
SDL_Mutex *SDL_CreateMutex(void) { SDL_Mutex *m=malloc(sizeof(*m)); assert(m); pthread_mutex_init(m,NULL);return m; }
SDL_Condition *SDL_CreateCondition(void) { SDL_Condition *c=malloc(sizeof(*c));assert(c);pthread_cond_init(c,NULL);return c; }
void SDL_LockMutex(SDL_Mutex *m) { assert(!pthread_mutex_lock(m)); }
void SDL_UnlockMutex(SDL_Mutex *m) { assert(!pthread_mutex_unlock(m)); }
void SDL_WaitCondition(SDL_Condition *c,SDL_Mutex *m) { assert(!pthread_cond_wait(c,m)); }
void SDL_SignalCondition(SDL_Condition *c) { assert(!pthread_cond_signal(c)); }
struct ThreadCall { int (*fn)(void *); void *arg; };
static void *thread_start(void *v) { struct ThreadCall c=*(struct ThreadCall *)v; free(v); c.fn(c.arg); return NULL; }
SDL_Thread *SDL_CreateThread(int (*fn)(void *),const char *name,void *arg) {
    (void)name; SDL_Thread *t=malloc(sizeof(*t)); struct ThreadCall *c=malloc(sizeof(*c)); assert(t&&c);c->fn=fn;c->arg=arg;
    assert(!pthread_create(t,NULL,thread_start,c));pthread_detach(*t);return t;
}
bool SDL_SetCurrentThreadPriority(int p) { (void)p;return true; }
int SDL_GetSystemRAM(void) { return 8192; }
void *SDL_LoadFile(const char *path,size_t *size) {
    /* 512x512 BC1, decoded to >1 MB, deliberately larger than the test budget. */
    (void)path; uint32_t h[32]={0}; uint8_t *f=calloc(1,128+131072); assert(f);
    memcpy(f,"DDS ",4);h[3]=512;h[4]=512;h[7]=1;h[20]=4;h[21]=0x31545844;
    memcpy(f+4,(uint8_t *)h+4,124);*size=128+131072;return f;
}
SDL_Surface *SDL_LoadPNG(const char *p) { (void)p; return NULL; }
SDL_Surface *SDL_ConvertSurface(SDL_Surface *p,int f) { (void)p;(void)f;return NULL; }
SDL_Surface *SDL_ScaleSurface(SDL_Surface *p,int w,int h,int f) { (void)p;(void)w;(void)h;(void)f;return NULL; }
void SDL_DestroySurface(SDL_Surface *p) { (void)p; }
bool SDL_GetPathInfo(const char *p,SDL_PathInfo *i) { (void)p;(void)i;return false; }
bool SDL_EnumerateDirectory(const char *p,SDL_EnumerationResult (*f)(void *,const char *,const char *),void *u) { (void)p;(void)f;(void)u;return true; }
static void pause_ms(void) { struct timespec t={0,1000000};nanosleep(&t,NULL); }
int main(void) {
    setenv("BT3_PACK_MB","1",1);
    sCount=12; sEntries=calloc(sCount,sizeof(*sEntries));assert(sEntries);
    for (unsigned i=0;i<sCount;i++) sEntries[i].path=strdup("fake.dds");
    TexPackImage img;
    /* Fill the queue, then give the worker time to hit backpressure. */
    for (unsigned i=0;i<sCount;i++) assert(TexPack_Get((int)i,&img)>=0);
    for (int i=0;i<50;i++) pause_ms();
    SDL_LockMutex(sLock);
    assert(sHeldCount==1 && sHeldBytes==(size_t)512*512*4);
    SDL_UnlockMutex(sLock);
    /* Switching requested images must release a single oversized entry and
       wake the reader: this catches a permanent queue-stall regression. */
    for (unsigned id=0;id<sCount;id++) {
        int ready=0;
        for (int tries=0;tries<2000 && !ready;tries++) {
            int r=TexPack_Get((int)id,&img);assert(r>=0);
            if (r==1) { assert(img.w==512 && img.h==512 && img.format==0); volatile uint8_t px=img.data[0][0];(void)px;ready=1; }
            else pause_ms();
            SDL_LockMutex(sLock);
            assert(sHeldBytes <= sBudget + (size_t)512*512*4);
            SDL_UnlockMutex(sLock);
        }
        assert(ready);
    }
    GsPerf_SetMemoryPressure(2);
    TexPack_Get(0,&img);
    SDL_LockMutex(sLock);assert(sBudget==((size_t)1<<19));SDL_UnlockMutex(sLock);
    puts("PASS: real async DDS cache, decompression, bounded memory, oversized entries, eviction, wake-up and pressure");
    return 0;
}
