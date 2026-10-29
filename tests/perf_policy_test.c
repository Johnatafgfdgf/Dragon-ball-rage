#include <assert.h>
#include <stdio.h>
#include <pthread.h>
#include "gs_perf.h"
#include "gs_texpack_budget.h"
int Port_Setting(const char *key, int def) { (void)key; return def; }
static void *publish(void *unused) {
    (void)unused;
    for (int i = 0; i < 10000; i++) {
        GsPerf_SetMemoryPressure(i % 3);
        GsPerf_SetRefreshMilliHz(60000 + (i % 2) * 60000);
        GsPerf_Present(i % 2 ? 'B' : 'D');
    }
    return NULL;
}
int main(void) {
    const uint64_t tick = 33366700ull;
    uint64_t now = 1000000000ull;
    DrFramePolicy p = {0};
    assert(DrFramegenMultiplier(0) == 1 && DrFramegenMultiplier(1) == 2);
    assert(DrFramegenMultiplier(2) == 4 && DrFramegenMultiplier(3) == 4 && DrFramegenMultiplier(4) == 3);
    assert(DrDisplayCap(4, 59940) == 2 && DrDisplayCap(4, 90000) == 3 && DrDisplayCap(4, 119880) == 4);
    assert(DrDisplayCap(4, 0) == 2 && DrDisplayCap(4, 30000) == 1);
    assert(DrDisplayCap(3, 120000) == 2 && DrDisplayCap(2, 90000) == 1);
    assert(DrFramegenSteps(1, 1) == 1 && DrFramegenSteps(2, 2) == 2);
    assert(DrFramegenSteps(4, 2) == 4 && DrFramegenSteps(4, 1) == 2);
    assert(DrFramegenSteps(3, 2) == 3 && DrFramegenSteps(3, 1) == 1);
    for (int i = 0; i < 100; i++) DrFramePolicySample(&p, 4000000, now += 8333333, tick, 4, 0, 1);
    assert(p.cap == 4);
    /* A single effect-load spike must not switch modes. */
    DrFramePolicySample(&p, 100000000, now += 8333333, tick, 4, 0, 1);
    assert(p.cap == 4);
    for (int i = 0; i < 60; i++) DrFramePolicySample(&p, 24000000, now += 24000000, tick, 4, 0, 1);
    assert(p.cap == 1);
    /* Recovery cannot bounce straight back to 4x. */
    for (int i = 0; i < 40; i++) DrFramePolicySample(&p, 4000000, now += 8333333, tick, 4, 0, 1);
    assert(p.cap == 1);
    for (int i = 0; i < 1000; i++) DrFramePolicySample(&p, 4000000, now += 8333333, tick, 4, 0, 1);
    assert(p.cap == 4);
    assert(DrFramePolicySample(&p, 4000000, ++now, tick, 4, 3, 1) == 1);
    assert(DrFramePolicySample(&p, 4000000, ++now, tick, 4, 2, 0) == 2);
    assert(DrFramePolicySample(&p, 4000000, ++now, tick, 4, 3, 0) == 1);
    /* Healthy FIFO/VSync cost at 60 Hz must retain 2x. */
    p = (DrFramePolicy){0};
    for (int i = 0; i < 1000; i++) DrFramePolicySample(&p, 16683350, now += 16683350, tick, 2, 0, 1);
    assert(p.cap == 2);
    assert(TexPack_DefaultBudgetBytes(2048) == ((size_t)64 << 20));
    assert(TexPack_DefaultBudgetBytes(8192) == ((size_t)256 << 20));
    assert(DrCacheLimit(256u << 20, 1) == (192u << 20));
    assert(DrCacheLimit(256u << 20, 2) == (128u << 20));
    pthread_t ts[4];
    for (int i=0; i<4; i++) assert(!pthread_create(&ts[i], NULL, publish, NULL));
    for (int i=0; i<4; i++) assert(!pthread_join(ts[i], NULL));
    assert(GsPerf_MemoryPressure() == 2);
    assert(GsPerf_RefreshMilliHz() == 60000 || GsPerf_RefreshMilliHz() == 120000);
    for (int i=0; i<121; i++) GsPerf_Tick(tick, 4000000, tick, 2000000, 2000000, 100000, 100000);
    puts("PASS: framegen, display, thermal, recovery, cache limits and concurrent telemetry");
    return 0;
}
