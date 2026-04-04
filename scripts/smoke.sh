#!/usr/bin/env bash
# Isolated smoke test for reflect CLI (no Entire required).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

cp "$ROOT/reflect" "$TMP/reflect"
chmod +x "$TMP/reflect"
cp -R "$ROOT/lib" "$TMP/lib"
cp -R "$ROOT/templates" "$TMP/templates"
cp -R "$ROOT/skill" "$TMP/skill"
cp -R "$ROOT/hooks" "$TMP/hooks"

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
test -f .reflect/format.yaml
run ./reflect context
test -s .reflect/context.md
run ./reflect status
run ./reflect search smoke
run ./reflect improve
run ./reflect metrics | python3 -c "import json,sys; json.load(sys.stdin)"

echo "smoke OK"
