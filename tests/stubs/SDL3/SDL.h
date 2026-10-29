/* Host cache-concurrency test shim. Production compiles against real SDL3. */
#ifndef DR_TEST_SDL_H
#define DR_TEST_SDL_H
#include <pthread.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdbool.h>
#include <strings.h>
#define SDLCALL
#define SDL_free free
#define SDL_malloc malloc
#define SDL_strcasecmp strcasecmp
#define SDL_THREAD_PRIORITY_LOW 0
#define SDL_PIXELFORMAT_RGBA32 1
#define SDL_SCALEMODE_LINEAR 1
#define SDL_PATHTYPE_DIRECTORY 1
#define SDL_ENUM_CONTINUE 0
typedef pthread_mutex_t SDL_Mutex;
typedef pthread_cond_t SDL_Condition;
typedef pthread_t SDL_Thread;
typedef int SDL_EnumerationResult;
typedef struct { int type; } SDL_PathInfo;
typedef struct { int w,h,pitch; void *pixels; } SDL_Surface;
SDL_Mutex *SDL_CreateMutex(void);
SDL_Condition *SDL_CreateCondition(void);
void SDL_LockMutex(SDL_Mutex *);
void SDL_UnlockMutex(SDL_Mutex *);
void SDL_WaitCondition(SDL_Condition *, SDL_Mutex *);
void SDL_SignalCondition(SDL_Condition *);
SDL_Thread *SDL_CreateThread(int (*)(void *), const char *, void *);
bool SDL_SetCurrentThreadPriority(int);
int SDL_GetSystemRAM(void);
void *SDL_LoadFile(const char *, size_t *);
SDL_Surface *SDL_LoadPNG(const char *);
SDL_Surface *SDL_ConvertSurface(SDL_Surface *, int);
SDL_Surface *SDL_ScaleSurface(SDL_Surface *, int, int, int);
void SDL_DestroySurface(SDL_Surface *);
bool SDL_GetPathInfo(const char *, SDL_PathInfo *);
bool SDL_EnumerateDirectory(const char *, SDL_EnumerationResult (*)(void *,const char *,const char *), void *);
#endif
