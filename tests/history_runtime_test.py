#!/usr/bin/env python3
"""Compile the actual interpolation-history lifecycle functions in a host harness."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile

root = Path(sys.argv[1]).resolve()
source = (root / 'port/src/gs/gs_draw.c').read_text()
primitive = source[source.index('typedef struct InterpPrim {'):source.index('} InterpPrim;') + len('} InterpPrim;')]
start = source.index('static void interp_buffers_free(void)')
end = source.index('void GsGpu_FrameEnd(void)', start)
functions = source[start:end]
harness = r'''
#include <assert.h>
#include <stdio.h>
#include "gs_draw.h"
#include "gs_perf.h"
PRIMITIVE
#define INTERP_MAX_PRIMS (MAX_VERTS / 3)
static Vu0Uniform *sInterpPrev,*sInterpBlend;
static uint32_t *sInterpPrevSig,*sInterpSig,*sInterpPrevByKind;
static Vtx *sInterpPrevVerts,*sInterpBlendVerts;
static InterpPrim *sInterpPrevPrims,*sInterpPrims;
static uint8_t *sInterpPrimUsed;
static uint32_t sInterpPrevCount,sInterpPrevPrimCount,sInterpPrevVertCount,sInterpPrimCount;
static int sInterpNext,sInterpRepeat;
static int calls,failAt,live;
static void *test_malloc(size_t size) {
    if (++calls==failAt) return NULL;
    void *p=malloc(size);if(p) live++;return p;
}
static void test_free(void *p) { if(p)live--;free(p); }
#define malloc test_malloc
#define free test_free
FUNCTIONS
#undef malloc
#undef free
int main(void) {
    for (int failure=1;failure<=9;failure++) {
        calls=live=0;failAt=failure;
        assert(!interp_buffers_alloc());
        assert(live==0 && sInterpPrev==NULL && sInterpPrims==NULL);
    }
    for (int turn=0;turn<2;turn++) {
        calls=live=failAt=0;
        assert(interp_buffers_alloc() && live==9);
        assert(sInterpPrev && sInterpBlend && sInterpPrevVerts && sInterpBlendVerts && sInterpPrims);
        assert(interp_buffers_alloc() && live==9 && calls==9); /* no allocation each frame */
        sInterpPrevCount=sInterpPrevVertCount=8;sInterpNext=2;sInterpRepeat=1;
        interp_buffers_free();
        assert(live==0 && !sInterpPrev && !sInterpBlend && !sInterpPrims && !sInterpPrevVerts);
        assert(!sInterpNext && !sInterpRepeat && !sInterpPrevCount && !sInterpPrevVertCount);
    }
    size_t reserved=2*MAX_VU_UNIFORMS*sizeof(Vu0Uniform)+2*MAX_VU_UNIFORMS*sizeof(uint32_t)+
        2*MAX_VERTS*sizeof(Vtx)+2*INTERP_MAX_PRIMS*sizeof(InterpPrim)+INTERP_MAX_PRIMS;
    printf("PASS: real history lifecycle, nine allocation-failure paths, reuse, release; %.2f MiB capacity\n",reserved/1048576.0);
    return 0;
}
'''.replace('PRIMITIVE', primitive).replace('FUNCTIONS', functions)
with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp)
    (path/'test.c').write_text(harness)
    subprocess.run(['cc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror',
        '-fsanitize=address,undefined','-fno-omit-frame-pointer',
        '-I'+str(root/'port/src/gs'),str(path/'test.c'),'-o',str(path/'test')],check=True)
    subprocess.run([str(path/'test')],env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0'},check=True)
