#include <assert.h>
#include <stdio.h>
#include "gs_perf.h"
int main(void) {
    const uint64_t tick=33366700ull;
    uint64_t now=1000000000ull;
    DrFramePolicy old={0};
    DrOpticalPolicy flow={0};
    /* Regression: phone log shows ~20 ms scene backend, ~30 fps source.
       Geometry replay policy disables 2x; image-only 20+1 ms fits the tick. */
    for (int i=0;i<900;i++) {
        now+=tick;
        DrFramePolicySample(&old,20000000,now,tick,2,0,1);
        DrOpticalPolicyExtra(&flow,1000000);
        assert(DrOpticalPolicySample(&flow,20000000,now,tick,2,0,1)==2);
    }
    assert(old.cap==1);
    /* Source renders once for every multiplier. */
    for(int n=2;n<=4;n++) {
        flow=(DrOpticalPolicy){0};
        for(int i=0;i<300;i++) {
            DrOpticalPolicyExtra(&flow,1000000);
            assert(DrOpticalPolicySample(&flow,26000000,now+=tick,tick,n,0,1)==n);
        }
    }
    /* Expensive extras reduce 4x to 2x, rather than disabling all FG. */
    flow=(DrOpticalPolicy){0};
    for(int i=0;i<120;i++) {
        DrOpticalPolicyExtra(&flow,4000000);
        DrOpticalPolicySample(&flow,27000000,now+=tick,tick,4,0,1);
    }
    assert(flow.source.cap==2);
    /* True source overload still drops to 1x; recovery is delayed and staged. */
    for(int i=0;i<120;i++) DrOpticalPolicySample(&flow,45000000,now+=tick,tick,4,0,1);
    assert(flow.source.cap==1);
    for(int i=0;i<40;i++) {
        DrOpticalPolicyExtra(&flow,1000000);
        DrOpticalPolicySample(&flow,20000000,now+=tick,tick,4,0,1);
        assert(flow.source.cap==1);
    }
    int saw2=0,saw3=0;
    for(int i=0;i<700;i++) {
        DrOpticalPolicyExtra(&flow,1000000);
        int cap=DrOpticalPolicySample(&flow,20000000,now+=tick,tick,4,0,1);
        if(cap==2)saw2=1;
        if(cap==3)saw3=1;
    }
    assert(saw2 && saw3 && flow.source.cap==4);
    /* FIFO presentation blocking is allowed if source + endpoint fits. */
    flow=(DrOpticalPolicy){0};
    for(int i=0;i<300;i++) {
        DrOpticalPolicyExtra(&flow,16683350);
        assert(DrOpticalPolicySample(&flow,16683350,now+=tick,tick,2,0,1)==2);
    }
    assert(DrOpticalPolicySample(&flow,20000000,now+=tick,tick,4,3,0)==1);
    assert(DrOpticalPolicySample(&flow,20000000,now+=tick,tick,4,2,0)==2);
    assert(DrOpticalPolicySample(&flow,20000000,now+=tick,tick,1,0,0)==1);
    assert(DrOpticalPolicySample(&flow,20000000,now+=tick,tick,4,0,0)==4);
    puts("PASS optical budget: phone regression, one scene per tick, 2x/3x/4x, overload, staged recovery, VSync, hard limits");
}
