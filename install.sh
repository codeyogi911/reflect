#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── CLI: symlink to ~/.local/bin ──────────────────────────────────────
BIN_DIR="${HOME}/.local/bin"
mkdir -p "$BIN_DIR"
ln -sf "$SCRIPT_DIR/reflect" "$BIN_DIR/reflect"
echo "CLI installed: $BIN_DIR/reflect"

# ── Skill: install into target repo ──────────────────────────────────
# If run from within a git repo, install the skill there.
# Otherwise install into the reflect repo itself.
TARGET_REPO="${1:-$(git rev-parse --show-toplevel 2>/dev/null || echo "$SCRIPT_DIR")}"

SKILL_SRC="$SCRIPT_DIR/skill/SKILL.md"
SKILL_DST="$TARGET_REPO/.claude/skills/reflect"

mkdir -p "$SKILL_DST"
cp "$SKILL_SRC" "$SKILL_DST/SKILL.md"

# Copy hooks if they exist
HOOKS_DIR="$SCRIPT_DIR/hooks"
if [ -d "$HOOKS_DIR" ]; then
    rm -rf "$SKILL_DST/hooks"
    cp -R "$HOOKS_DIR" "$SKILL_DST/hooks"
fi

echo "Skill installed: $SKILL_DST/SKILL.md"

# ── Summary ──────────────────────────────────────────────────────────
echo ""
echo "Make sure $BIN_DIR is on your PATH."
echo "Run 'reflect init' in any git repo to get started."
