#!/bin/sh
set -eu
ROOT=$(cd "${1:-upstream}" && pwd)
TESTS=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SDL_ROOT=${DR_FG_SDL_ROOT:?provide built SDL 3.4.12 folder (include/ and libSDL3.so)}
SDL_INCLUDE=${DR_FG_SDL_INCLUDE:-$SDL_ROOT/include}
GLSLANG=${DR_FG_GLSLANG:-glslangValidator}
SPIRV_VAL=${DR_FG_SPIRV_VAL:-spirv-val}
export ROOT GLSLANG SPIRV_VAL
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
export DR_FG_TEST_GEN="$TMP"
python3 - <<'PY'
from pathlib import Path
import os, subprocess
root=Path(os.environ['ROOT']);gen=Path(os.environ['DR_FG_TEST_GEN']);arrays=[]
for p in sorted((root/'port/src/gs/shaders').glob('fg_*.comp')):
    spv=gen/(p.name+'.spv')
    subprocess.run([os.environ['GLSLANG'],'-V','--target-env','vulkan1.1',str(p),'-o',str(spv)],check=True)
    subprocess.run([os.environ['SPIRV_VAL'],'--target-env','vulkan1.1',str(spv)],check=True)
    name='k'+p.stem.capitalize()+'CompSpv'
    arrays.append('static const unsigned char '+name+'[] = {'+','.join(map(str,spv.read_bytes()))+'};\n')
assert len(arrays)==7
(gen/'shaders.h').write_text(''.join(arrays))
PY
cc -std=gnu11 -O1 -g -Wall -Wextra -Werror -fsanitize=address,undefined -fno-omit-frame-pointer \
  -I"$SDL_INCLUDE" -I"$TMP" -I"$ROOT/port/src/gs" \
  "$TESTS/optical_gpu_test.c" "$ROOT/port/src/gs/gs_optical.c" \
  -L"$SDL_ROOT" -Wl,-rpath,"$SDL_ROOT" -lSDL3 -lm -o "$TMP/optical"
cc -std=gnu11 -O1 -g -Wall -Wextra -Werror -fsanitize=address,undefined -fno-omit-frame-pointer \
  -ffunction-sections -fdata-sections -I"$SDL_INCLUDE" -I"$TMP" -I"$ROOT/port/src/gs" \
  "$TESTS/optical_init_test.c" -Wl,--gc-sections -o "$TMP/init"
ASAN_OPTIONS=detect_leaks=0 "$TMP/init"
SDL_VIDEODRIVER=offscreen ASAN_OPTIONS=detect_leaks=0 "$TMP/optical"
