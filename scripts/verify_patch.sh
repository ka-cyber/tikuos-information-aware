#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
cp -a "$ROOT/upstream/tikuOS" "$TMP/tikuOS"
cd "$TMP/tikuOS"
patch --dry-run -p1 < "$ROOT/patches/0001-information-utility-scheduler.patch" >/dev/null
echo "patch verification: PASS"
