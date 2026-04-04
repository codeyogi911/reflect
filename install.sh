#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── Phase 1: Install runtime files ──────────────────────────────────
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/reflect"
BIN_DIR="${HOME}/.local/bin"

mkdir -p "$DATA_DIR" "$BIN_DIR"

# Copy runtime files (idempotent — overwrites previous install)
cp "$SCRIPT_DIR/reflect" "$DATA_DIR/reflect"
chmod +x "$DATA_DIR/reflect"

rm -rf "$DATA_DIR/lib"
cp -R "$SCRIPT_DIR/lib" "$DATA_DIR/lib"

rm -rf "$DATA_DIR/skill"
cp -R "$SCRIPT_DIR/skill" "$DATA_DIR/skill"

if [ -d "$SCRIPT_DIR/hooks" ]; then
    rm -rf "$DATA_DIR/hooks"
    cp -R "$SCRIPT_DIR/hooks" "$DATA_DIR/hooks"
fi

[ -f "$SCRIPT_DIR/LICENSE" ] && cp "$SCRIPT_DIR/LICENSE" "$DATA_DIR/LICENSE"

# Symlink into PATH
ln -sf "$DATA_DIR/reflect" "$BIN_DIR/reflect"

echo "Installed to: $DATA_DIR"
echo "CLI symlink:  $BIN_DIR/reflect"

# ── Phase 2: Per-project skill (optional) ───────────────────────────
TARGET_REPO="${1:-$(git rev-parse --show-toplevel 2>/dev/null || true)}"

if [ -n "$TARGET_REPO" ] && [ -d "$TARGET_REPO/.git" ]; then
    SKILL_DST="$TARGET_REPO/.claude/skills/reflect"
    mkdir -p "$SKILL_DST"
    cp "$DATA_DIR/skill/SKILL.md" "$SKILL_DST/SKILL.md"

    if [ -d "$DATA_DIR/hooks" ]; then
        rm -rf "$SKILL_DST/hooks"
        cp -R "$DATA_DIR/hooks" "$SKILL_DST/hooks"
    fi

    echo "Skill installed: $SKILL_DST/SKILL.md"
fi

echo ""
echo "Make sure $BIN_DIR is on your PATH."
echo "Run 'reflect init' in any git repo to get started."
