#!/usr/bin/env python3
"""Apply the experimental adaptive texture-cache policy to upstream Android v0.9.0."""
from pathlib import Path
p = Path("port/src/gs/gs_texpack.c")
s = p.read_text()
def swap(before, after):
    global s
    assert s.count(before) == 1, f"upstream mismatch: {before[:65]!r}"
    s = s.replace(before, after, 1)
swap('#include "gs_texpack.h"', '#include "gs_texpack.h"\n#include "gs_texpack_budget.h"')
swap('''#ifdef __ANDROID__
#define TEXPACK_BUDGET ((size_t)256 << 20)  /* (a phone: the memory is the system's and the GPU's too) */
#else
#define TEXPACK_BUDGET ((size_t)1024 << 20) /* the files kept in memory: one session's two fights took 289 MB */
#endif''', '/* RAM-adaptive default; BT3_PACK_MB still overrides it. */')
swap('''        sSync = getenv("BT3_PACK_SYNC") != NULL && atoi(getenv("BT3_PACK_SYNC")) != 0;
        sBudget = mb != NULL && atoi(mb) > 0 ? (size_t)atoi(mb) << 20 : TEXPACK_BUDGET;''',
'''        const int ramMB = SDL_GetSystemRAM();
        sSync = getenv("BT3_PACK_SYNC") != NULL && atoi(getenv("BT3_PACK_SYNC")) != 0;
        sBudget = mb != NULL && atoi(mb) > 0 ? (size_t)atoi(mb) << 20 :
                  TexPack_DefaultBudgetBytes(ramMB > 0 ? (unsigned)ramMB : 0u);
        fprintf(stderr, "bt3: texture pack cache budget: %zu MB (RAM %d MB)\\n",
                sBudget >> 20, ramMB);''')
swap('''    r = e->state == 2 ? 1 : e->state == 3 ? -1 : 0;
    if (r == 1) {
        *img = e->img;
        trim((uint32_t)id);
    }''',
'''    /* Reclaim completed queued uploads even while this texture is pending;
       eviction remains on the render thread to protect upload pointers. */
    trim((uint32_t)id);
    r = e->state == 2 ? 1 : e->state == 3 ? -1 : 0;
    if (r == 1) {
        *img = e->img;
    }''')
p.write_text(s)
h = Path("port/src/gs/gs_texpack_budget.h")
h.write_text("""#ifndef GS_TEXPACK_BUDGET_H
#define GS_TEXPACK_BUDGET_H
#include <stddef.h>
static inline size_t TexPack_DefaultBudgetBytes(unsigned physicalRamMB) {
#ifdef __ANDROID__
    const unsigned budgetMB = physicalRamMB == 0 ? 128u :
                              physicalRamMB <= 3072 ? 64u :
                              physicalRamMB <= 4500 ? 128u :
                              physicalRamMB <= 6500 ? 192u : 256u;
    return (size_t)budgetMB << 20;
#else
    (void)physicalRamMB;
    return (size_t)1024 << 20;
#endif
}
#endif
""")
print("Applied opt1 texture cache patch")
