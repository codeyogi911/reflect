#!/usr/bin/env bash
# Isolated smoke test for reflect CLI (no Entire required).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

mkdir -p "$TMP/harness"
cp "$ROOT/reflect" "$TMP/reflect"
chmod +x "$TMP/reflect"
cp -R "$ROOT/lib" "$TMP/lib"
cp "$ROOT/harness/default.py" "$TMP/harness/default.py"

cd "$TMP"
git init -q
git config user.email "smoke@example.com"
git config user.name "Smoke"
git commit --allow-empty -m "smoke"

run() {
  echo "+ $*" >&2
  "$@"
}

run ./reflect
run ./reflect init
test -f .reflect/harness
run ./reflect context
test -s .reflect/context.md
run ./reflect status
run ./reflect search smoke
run ./reflect improve
run ./reflect metrics | python3 -c "import json,sys; json.load(sys.stdin)"

echo "smoke OK"
