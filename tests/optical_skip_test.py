#!/usr/bin/env python3
"""Exercise the production skipped-source branch, preserving only visual history."""
from pathlib import Path
import os,subprocess,sys,tempfile
root=Path(sys.argv[1]);s=(root/'port/src/gs/gs_draw.c').read_text()
start=s.index('    if (gsSkipFrame) {',s.index('void GsGpu_FrameEnd'))
end=s.index('{',start)+1;d=1
while d:d+=(s[end]=='{')-(s[end]=='}');end+=1
prefix=r'''
#include <assert.h>
#include <stdio.h>
#include "gs_fg_trace.h"
static int gsSkipFrame=1,sInterpNext=2,sInterpPrevCount=7,sInterpPrevPrimCount=8;
static int gsVertCount=1,gsVuVertCount=2,gsVuIdxCount=3,gsVuUniCount=4,gsDrawCount=5;
static int flush,historyReset,skip;
static void GsGpu_InterpPump(int ahead,int all){assert(ahead==0 && all==1);flush++;sInterpNext=0;}
void GsVkOptical_Reset(int release){(void)release;historyReset++;}
void GsFg_Event(int stage,uint64_t id,int64_t value,uint64_t detail){assert(stage==FG_SKIP && !id && value==1 && !detail);skip++;}
static void skip_decide(void){}
'''
main=r'''
int main(void){
 source_skip();assert(flush==1 && !historyReset && skip==1);
 assert(!sInterpPrevCount && !sInterpPrevPrimCount);
 assert(!gsVertCount && !gsVuVertCount && !gsVuIdxCount && !gsVuUniCount && !gsDrawCount);
 source_skip();assert(flush==1 && !historyReset && skip==2);
 puts("PASS production skipped source: pending endpoint flushed, optical history retained, geometry cleared, no new visual source");
}
'''
with tempfile.TemporaryDirectory() as tmp:
    p=Path(tmp);(p/'test.c').write_text(prefix+'static void source_skip(void){\n'+s[start:end]+'\n}\n'+main)
    subprocess.run(['cc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
        '-I'+str(root/'port/src/gs'),str(p/'test.c'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0'})
