#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="${1:-$(git -C "$SCRIPT_DIR" describe --tags --always 2>/dev/null || echo "dev")}"
STAGING="$(mktemp -d)"
trap 'rm -rf "$STAGING"' EXIT

DEST="$STAGING/reflect-$VERSION"
mkdir -p "$DEST"

# Copy only runtime files
cp "$SCRIPT_DIR/reflect" "$DEST/reflect"
cp "$SCRIPT_DIR/install.sh" "$DEST/install.sh"
cp -R "$SCRIPT_DIR/lib" "$DEST/lib"
cp -R "$SCRIPT_DIR/skill" "$DEST/skill"
cp -R "$SCRIPT_DIR/hooks" "$DEST/hooks"
[ -f "$SCRIPT_DIR/LICENSE" ] && cp "$SCRIPT_DIR/LICENSE" "$DEST/LICENSE"

# Clean Python artifacts
find "$DEST" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find "$DEST" -name '*.pyc' -delete 2>/dev/null || true

# Build archive
OUTPUT="$SCRIPT_DIR/reflect-$VERSION.tar.gz"
tar -czf "$OUTPUT" -C "$STAGING" "reflect-$VERSION"
echo "$OUTPUT"
