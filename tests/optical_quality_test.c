#include "gs_perf.h"
#include <assert.h>
#include <stdio.h>
int main(void) {
 DrOpticalQualityPolicy p={0};uint64_t t=1,step=33333333;
 assert(DrOpticalQualitySample(&p,2,1,0,step,t)==2);
 /* Warmup is bounded, one transient cannot lower quality. */
 t+=2000000000;assert(DrOpticalQualitySample(&p,2,1,20000000,step,t)==2);
 for(int i=0;i<7;i++){t+=step;DrOpticalQualitySample(&p,2,1,20000000,step,t);}
 assert(p.quality==1);
 /* New cheap results do not oscillate quality back immediately. */
 for(int i=0;i<600;i++){t+=step;DrOpticalQualitySample(&p,2,1,1000000,step,t);assert(p.quality==1);}
 for(int i=0;i<600;i++){t+=step;DrOpticalQualitySample(&p,2,1,1000000,step,t);}
 assert(p.quality==2);
 assert(DrOpticalQualitySample(&p,0,1,1000000,step,t)==0);
 assert(DrOpticalQualitySample(&p,2,0,100000000,step,t)==2);
 assert(DrTickDisplaySteps(2,60000,29262544)==1); /* 114% online cannot fit full 2x at 60Hz */
 assert(DrTickDisplaySteps(2,120000,29262544)==2);
 assert(DrTickDisplaySteps(2,60000,33366700)==2);
 assert(DrTickDisplaySteps(3,90000,33366700)==3);
 assert(DrTickDisplaySteps(4,120000,33366700)==4);
 puts("PASS GPU quality hysteresis, manual preservation, real 30/60/90/120 Hz and 114% online display budget");
}
