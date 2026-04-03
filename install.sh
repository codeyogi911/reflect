#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR="$HOME/.claude/skills/reflect"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$SKILL_DIR"

ln -sf "$SCRIPT_DIR/SKILL.md" "$SKILL_DIR/SKILL.md"
ln -sf "$SCRIPT_DIR/templates" "$SKILL_DIR/templates"
ln -sf "$SCRIPT_DIR/hooks" "$SKILL_DIR/hooks"

echo "reflect installed to $SKILL_DIR"
echo "Run /reflect in any project to get started."
