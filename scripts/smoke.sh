#!/usr/bin/env bash
# Isolated smoke test for reflect CLI (no Entire required).
# Runs the installed `reflect` console script in a throwaway git repo.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

cd "$TMP"
git init -q
git config user.email "smoke@example.com"
git config user.name "Smoke"
git config commit.gpgsign false
git -c commit.gpgsign=false commit --allow-empty -m "smoke"

run() {
  echo "+ $*" >&2
  "$@"
}

# Use uv --project to ensure we hit the editable install from ROOT.
RUN="uv --project $ROOT run reflect"

run $RUN
run $RUN init --no-wiki
test -f .reflect/format.yaml
run $RUN status
run $RUN search smoke
run $RUN improve
run $RUN metrics | python3 -c "import json,sys; json.load(sys.stdin)"

echo "smoke OK"
