#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TMP="$ROOT/build/tikuOS-host"
rm -rf "$TMP"; mkdir -p "$ROOT/build"
cp -a "$ROOT/upstream/tikuOS" "$TMP"
cd "$TMP"
patch -p1 --forward --input "$ROOT/patches/0001-information-utility-scheduler.patch" >/dev/null 2>&1
gcc -std=c11 -O2 -Wall -Wextra -Werror -DTIKU_THREADS_MAX=4 -DTIKU_UTILITY_ENABLE=1 \
  -I"$ROOT/tests/c_host/include" -I"$TMP" \
  "$ROOT/tests/c_host/test_tiku_scheduler.c" \
  "$TMP/kernel/threads/tiku_thread.c" "$TMP/kernel/utility/tiku_utility.c" \
  -o "$ROOT/build/test_tiku_scheduler"
"$ROOT/build/test_tiku_scheduler"
