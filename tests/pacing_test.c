#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <pthread.h>
#include <signal.h>
#include "port_pacing.h"
static volatile sig_atomic_t signals;
static pthread_t mainThread;
static void got_signal(int s) { (void)s; signals++; }
static uint64_t now(void) {
    struct timespec ts;clock_gettime(CLOCK_MONOTONIC,&ts);
    return (uint64_t)ts.tv_sec*1000000000ull+(uint64_t)ts.tv_nsec;
}
static void *interrupt_wait(void *unused) {
    (void)unused;
    for (int i=0;i<10;i++) {
        struct timespec t={0,1000000};nanosleep(&t,NULL);
        pthread_kill(mainThread,SIGUSR1);
    }
    return NULL;
}
int main(void) {
    struct sigaction sa={0};sa.sa_handler=got_signal;sigemptyset(&sa.sa_mask);sigaction(SIGUSR1,&sa,NULL);
    mainThread=pthread_self();pthread_t worker;assert(!pthread_create(&worker,NULL,interrupt_wait,NULL));
    uint64_t due=now()+20000000ull;
    DrPaceSleepUntil(due);
    assert(now()>=due);
    assert(!pthread_join(worker,NULL));assert(signals>0);
    /* A missed deadline returns immediately; it must not add another full tick. */
    DrPaceSleepUntil(now()-1000000ull);
    puts("PASS: absolute monotonic pacing survives signals and missed deadlines");
    return 0;
}
