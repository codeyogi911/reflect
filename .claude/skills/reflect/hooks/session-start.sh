#!/usr/bin/env bash
# reflect SessionStart hook — checks if knowledge base needs updating.
# Uses .reflect/.last_run to compare against current Entire + git state.
# Non-blocking: always exits 0.

set -euo pipefail

# Skip if .reflect/ doesn't exist
if [ ! -d ".reflect" ]; then
  exit 0
fi

# Skip if reflect CLI isn't available
if ! command -v reflect &>/dev/null; then
  exit 0
fi

# Read session_start mode from config (default: auto)
MODE="auto"
if [ -f ".reflect/config.yaml" ]; then
  CONFIGURED=$(sed -n 's/^session_start:[[:space:]]*\([a-z]*\).*/\1/p' .reflect/config.yaml 2>/dev/null || true)
  if [ "$CONFIGURED" = "manual" ]; then
    MODE="manual"
  fi
fi

# Check if knowledge base needs updating by comparing .last_run state
NEEDS_UPDATE=false

if [ ! -f ".reflect/.last_run" ]; then
  NEEDS_UPDATE=true
else
  # Compare last known git SHA with current HEAD
  LAST_GIT=$(python3 -c "import json; print(json.load(open('.reflect/.last_run')).get('last_git_sha',''))" 2>/dev/null || true)
  CURRENT_GIT=$(git rev-parse --short HEAD 2>/dev/null || true)

  if [ -n "$CURRENT_GIT" ] && [ "$LAST_GIT" != "$CURRENT_GIT" ]; then
    NEEDS_UPDATE=true
  fi

  # Check if local reflect files changed since last run (cross-platform mtime)
  get_mtime() {
    if stat -c '%Y' /dev/null >/dev/null 2>&1; then
      stat -c '%Y' "$1" 2>/dev/null || echo "0"
    else
      stat -f '%m' "$1" 2>/dev/null || echo "0"
    fi
  }
  LAST_RUN_TS=$(get_mtime .reflect/.last_run)
  for f in .reflect/format.yaml .reflect/config.yaml; do
    if [ -e "$f" ]; then
      FILE_TS=$(get_mtime "$f")
      if [ "$FILE_TS" -gt "$LAST_RUN_TS" ]; then
        NEEDS_UPDATE=true
        break
      fi
    fi
  done

  # Compare last known Entire checkpoint with latest
  if command -v entire &>/dev/null; then
    LAST_CP=$(python3 -c "import json; print(json.load(open('.reflect/.last_run')).get('last_checkpoint',''))" 2>/dev/null || true)
    LATEST_CP=$(entire explain --short --search-all --no-pager 2>/dev/null | head -3 | sed -n 's/^\[\([a-f0-9-]*\)\].*/\1/p' | head -1 || true)
    if [ -n "$LATEST_CP" ] && [ "$LAST_CP" != "$LATEST_CP" ]; then
      NEEDS_UPDATE=true
    fi
  fi
fi

if [ "$NEEDS_UPDATE" = true ]; then
  if [ "$MODE" = "auto" ]; then
    echo "Reflect: New evidence detected. Updating knowledge base."
    echo "REFLECT_WIKI_INGEST"
  else
    echo "Reflect: New evidence detected. Run /reflect ingest to update the knowledge base."
  fi
fi

exit 0
