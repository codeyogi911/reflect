---
created: 2026-04-13
updated: 2026-04-13
sources: [commit bddce4c, checkpoint 4ecb34b81a12]
tags: [symlinks, skill-init, manifest]
status: active
---

# Symlink Hooks Directory Requires Special Handling

The `.claude/skills/reflect/hooks/` directory is created as a symlink by `reflect init` and cannot be reliably tracked via manifest files. Previous attempts to use manifest-based tracking for symlink contents were abandoned in favor of letting `reflect init` manage symlink creation directly.

## The Problem

When `reflect init` sets up the reflect skill, it creates `.claude/skills/reflect/hooks/` as a symlink (or symlinks within the hooks structure). Manifest tracking systems struggle with symlinks because:

- Git and file systems treat symlinks and their targets differently
- Reading/writing manifest files inside symlinked directories can cause stale references
- Changes to hook files may not sync cleanly through the manifest layer

This manifested as hook files (e.g., `session-start.sh`) being modified by init but not properly committed, caught by the stop hook validation. (checkpoint 4ecb34b81a12)

## The Solution

**Do not track symlink contents via manifest files.** Instead:

- Let `reflect init` create and manage the entire symlink structure
- Treat the hooks directory as init-owned; do not attempt post-hoc manifest synchronization
- If hooks need updating, modify them directly and rely on `reflect upgrade` to handle re-initialization
- If a manifest of symlink targets is needed, generate it separately from the hook files themselves (e.g., as read-only documentation)

## Related Decisions

The fix to abandon manifest tracking for symlinks (commit bddce4c) simplified the init flow and eliminated a class of sync bugs where manifest state diverged from actual filesystem state.
