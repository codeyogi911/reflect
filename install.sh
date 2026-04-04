#!/usr/bin/env bash
# reflect installer — curl -fsSL https://raw.githubusercontent.com/codeyogi911/reflect/main/install.sh | bash
set -euo pipefail

REPO="codeyogi911/reflect"
CLONE_DIR="${HOME}/.local/share/reflect"

info()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
err()   { printf '\033[1;31mError:\033[0m %s\n' "$*" >&2; exit 1; }

command_exists() { command -v "$1" >/dev/null 2>&1; }

# ── Preflight ──────────────────────────────────────────────────────
command_exists git    || err "git is required. Install it and try again."
command_exists python3 || err "python3 is required (3.11+). Install it and try again."

# ── Clone or update ────────────────────────────────────────────────
if [ -d "$CLONE_DIR" ]; then
    info "Updating existing install..."
    git -C "$CLONE_DIR" pull --ff-only origin main 2>/dev/null || {
        info "Pull failed, re-cloning..."
        rm -rf "$CLONE_DIR"
        git clone "https://github.com/${REPO}.git" "$CLONE_DIR"
    }
else
    info "Cloning reflect..."
    git clone "https://github.com/${REPO}.git" "$CLONE_DIR"
fi

# ── Install via pip ────────────────────────────────────────────────
info "Installing reflect CLI..."
if command_exists pipx; then
    pipx install --force "$CLONE_DIR"
elif command_exists pip; then
    pip install --user "$CLONE_DIR"
else
    # Last resort: install pip via ensurepip, then install
    python3 -m ensurepip --default-pip 2>/dev/null || true
    python3 -m pip install --user "$CLONE_DIR" || err "Could not install. Please install pip or pipx and try again."
fi

# ── Verify ─────────────────────────────────────────────────────────
if command_exists reflect; then
    info "reflect installed successfully!"
    echo ""
    reflect --help | head -3
else
    info "Install complete. Add ~/.local/bin to your PATH:"
    echo ""
    echo '  export PATH="$HOME/.local/bin:$PATH"'
    echo ""
    echo "Then restart your shell and run: reflect --help"
fi
