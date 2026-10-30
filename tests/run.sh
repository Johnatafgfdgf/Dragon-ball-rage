#!/bin/sh
set -eu
ROOT=${1:-upstream}
TESTS=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
cc -std=gnu11 -D__ANDROID__ -O1 -g -Wall -Wextra -Werror -pthread \
  -fsanitize=address,undefined -fno-omit-frame-pointer \
  -I"$ROOT/port/src/gs" "$TESTS/perf_policy_test.c" "$ROOT/port/src/gs/gs_perf.c" "$ROOT/port/src/gs/gs_fg_trace.c" -o "$TMP/policy"
ASAN_OPTIONS=detect_leaks=0 "$TMP/policy"
cc -std=gnu11 -O1 -g -Wall -Wextra -Werror -fsanitize=address,undefined \
  -I"$ROOT/port/src/gs" "$TESTS/optical_budget_test.c" -o "$TMP/optical-budget"
ASAN_OPTIONS=detect_leaks=0 "$TMP/optical-budget"
cc -std=gnu11 -D__ANDROID__ -O1 -g -Wall -Wextra -Werror -pthread \
  -Wno-unused-function -Wno-unused-variable -Wno-misleading-indentation \
  -fsanitize=address,undefined -fno-omit-frame-pointer -ffunction-sections -fdata-sections \
  -I"$TESTS/stubs" -I"$ROOT/port/src/gs" \
  "$TESTS/cache_runtime_test.c" "$ROOT/port/src/gs/gs_perf.c" "$ROOT/port/src/gs/gs_fg_trace.c" -Wl,--gc-sections -o "$TMP/cache"
ASAN_OPTIONS=detect_leaks=0 "$TMP/cache"
cc -std=gnu11 -O2 -Wall -Wextra -Werror -pthread -I"$ROOT/port/src" "$TESTS/pacing_test.c" -o "$TMP/pacing"
"$TMP/pacing"
python3 "$TESTS/history_runtime_test.py" "$ROOT"

cc -std=gnu11 -O1 -g -Wall -Wextra -Werror -pthread -fsanitize=address,undefined \
 -I"$ROOT/port/src/gs" "$TESTS/fg_trace_test.c" "$ROOT/port/src/gs/gs_fg_trace.c" -o "$TMP/trace"
ASAN_OPTIONS=detect_leaks=0 "$TMP/trace"
cc -std=gnu11 -O1 -g -Wall -Wextra -Werror -fsanitize=address,undefined \
 -I"$ROOT/port/src/gs" "$TESTS/optical_quality_test.c" -o "$TMP/quality"
ASAN_OPTIONS=detect_leaks=0 "$TMP/quality"

python3 "$TESTS/resim_thread_test.py" "$ROOT"

python3 "$TESTS/fg_pacing_clock_test.py" "$ROOT"

python3 "$TESTS/speed_bridge_abi_test.py" "$ROOT"
python3 "$TESTS/optical_cadence_test.py" "$ROOT"
python3 "$TESTS/optical_skip_test.py" "$ROOT"
