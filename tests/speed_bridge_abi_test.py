#!/usr/bin/env python3
"""Link the real C speed getter through its actual UI C++ declaration/call."""
from pathlib import Path
import re,subprocess,tempfile,sys
r=Path(sys.argv[1]);ui=(r/'port/src/gs/ui.cpp').read_text();inc=(r/'port/src/gs/ui_android.inc').read_text()
start=ui.index('extern "C" {');end=ui.index('\nstatic bool sReady',start)
decl=re.search(r'^int Port_SpeedMilli\(void\);',ui[start:end],re.M);assert decl,'Port_SpeedMilli must be declared in the UI C-linkage block'
assert 'extern int Port_SpeedMilli' not in inc,'No local C++-linkage declaration'
call=re.search(r'nm_put\("fg_speed_milli",Port_SpeedMilli\(\)\);',inc);assert call
s=(r/'port/src/plat_stub.c').read_text();m=re.search(r'^int Port_SpeedMilli\(void\)\s*\{',s,re.M);assert m
i=s.index('{',m.start())+1;d=1
while d:d+=(s[i]=='{')-(s[i]=='}');i+=1
c='''static int active=1;
int Port_NetSession(void){return 0;} int Port_NetActive(void){return active;}
int Port_NetSpeedMilli(void){return 1140;} int Port_GameSpeed(void){return 90;}
void Test_NetOff(void){active=0;}
'''+s[m.start():i]
cpp='''#include <cassert>
#include <cstdio>
extern "C" {'''+decl[0]+'''void Test_NetOff(void);}
static int captured;static void nm_put(const char *,int n){captured=n;}
int main(){'''+call[0]+'''assert(captured==1140);Test_NetOff();'''+call[0]+'''assert(captured==900);
 puts("PASS C/C++ speed bridge: real C getter links once, negotiated online speed, offline speed preserved");}
'''
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp);(p/'port.c').write_text(c);(p/'ui.cpp').write_text(cpp)
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror','-c',str(p/'port.c'),'-o',str(p/'port.o')],check=True)
 subprocess.run(['c++','-std=c++17','-Wall','-Wextra','-Werror',str(p/'ui.cpp'),str(p/'port.o'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
