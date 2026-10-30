#!/usr/bin/env python3
"""Execute the actual engine menu handler: live controls must reach saved runtime settings."""
from pathlib import Path
import os,re,subprocess,sys,tempfile
text=(Path(sys.argv[1])/'port/src/gs/ui_android.inc').read_text()
start=text.index('static void nm_apply(');opening=text.index('{',start);end=opening+1;depth=1
while depth:
    depth+=(text[end]=='{')-(text[end]=='}');end+=1
handler=text[start:end]
for key in ('dr_fg_method','dr_fg_quality','dr_fg_hud'):
    assert 'nm_put("'+key+'",' in text,'missing native snapshot '+key
calls=set(re.findall(r'\b([A-Za-z_]\w*)\s*\(',handler))
ignored={'if','sizeof','nm_apply','strcmp','memcmp','save_setting','GsGpu_GetSettings','GsGpu_SetSettings'}
prefix=r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
typedef struct { int scale4,aspectMilli,filter,smooth2d,texPack,frameSkip,fxOff,glow,music,effects,voices,stage,hudLayout,menuFont,battleFont,textFont; } PortVideo;
static int gGsFragDepth,gsInterp,sGL,sMeter,gPortMusicFollows,sBars,gPortUnlockAll;
static int savedValue,saves;
static char savedKey[24];
static void GsGpu_GetSettings(PortVideo *v) { memset(v,0,sizeof(*v)); }
static void GsGpu_SetSettings(PortVideo *v) { (void)v;assert(0 && "unrelated video state changed"); }
static void unexpected(void) { assert(0 && "unexpected handler branch"); }
static void save_setting(const char *key,int value) { strcpy(savedKey,key);savedValue=value;saves++; }
'''
prefix+='\n'.join('#define '+name+'(...) unexpected()' for name in sorted(calls-ignored))+'\n'
main=r'''
static void expect(const char *key,int in,int out) {
 int before=saves;nm_apply(key,in);assert(saves==before+1 && !strcmp(key,savedKey) && savedValue==out);
}
int main(void) {
 expect("dr_fg_method",0,0);expect("dr_fg_method",1,1);
 expect("dr_fg_hud",0,0);expect("dr_fg_hud",1,1);
 expect("dr_fg_quality",-100,0);expect("dr_fg_quality",0,0);
 expect("dr_fg_quality",1,1);expect("dr_fg_quality",2,2);expect("dr_fg_quality",100,2);
 expect("dr_fg_auto",2,1);
 int before=saves;nm_apply("unknown_setting",1);assert(saves==before);
 puts("PASS production menu bridge: live method/quality/HUD, ranges, snapshots, unrelated keys");
}
'''
with tempfile.TemporaryDirectory() as tmp:
    p=Path(tmp);(p/'test.c').write_text(prefix+handler+main)
    subprocess.run(['cc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0'})
