---
created: 2026-04-09
updated: 2026-04-09
sources: [commit bddce4c]
tags: [hooks, symlink, installation, gotcha]
status: active
---

# Symlink Hooks Directory Handling

When `.claude/hooks` is a symlink to another directory — a common configuration for shared setups or templated deployments — hook installation logic must explicitly resolve the symlink to its real path. Naive path comparisons or file operations will either follow the symlink silently and write to the wrong location, or fail to recognize hooked paths as valid. (commit bddce4c)

## The Issue

If your project symlinks `.claude/hooks` to an external or shared directory, installer code that doesn't canonicalize paths will create inconsistent state:

- File operations follow the symlink transparently, writing hooks to the target directory instead of maintaining the `.claude/hooks` interface.
- Path existence or membership checks using string matching (e.g., `if '.claude/hooks' in path`) fail when the actual resolved path differs from the symlink.
- Validation logic sees different paths depending on whether it uses the symlink or the real path, leading to "hooks not found" errors despite correct installation.

## Solution

Always resolve symlinks to their canonical filesystem location before any path comparison or installation operation:

```python
import os
canonical_hooks_dir = os.path.realpath('.claude/hooks')
# Now use canonical_hooks_dir for all file ops and path checks
```

This ensures:
- Hook files are written to the correct physical location.
- Path validation consistently recognizes symlinked hooks directories.
- Upgrade and initialization routines find and manage existing hooks correctly.

The fix is essential if you support `.claude` as a shared package, monorepo submodule, or any setup where users symlink directories for deduplication.
