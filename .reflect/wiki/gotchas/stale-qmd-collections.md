---
created: 2026-04-13
updated: 2026-04-13
sources: [checkpoint 9c595bc9b42d]
tags: [qmd, initialization, cleanup]
status: active
---

# Stale qmd Collections Not Auto-Removed

When `.reflect/` is wiped clean (e.g., during testing or re-initialization), the qmd collection registration persists independently and retains stale path references pointing to files that no longer exist. This can cause query failures or incorrect behavior until the collection is manually removed.

## The Problem

The qmd collection is registered at the system level and maintains its own index files and metadata. Deleting `.reflect/` removes the wiki pages but leaves the collection intact with dangling references:

- `qmd update` and `qmd embed` will still reference paths that don't exist in the new `.reflect/` state
- Queries may fail or return incomplete results
- Re-running `reflect init` will not automatically re-register the collection if it already exists

## Solution

After wiping `.reflect/`, explicitly remove the qmd collection before proceeding:

```bash
qmd delete reflect-<repo-name>
```

Then run `reflect init` normally — it will detect the missing collection and register a fresh one.

## When You'll Hit This

This surfaces during test cycles when you want to validate the initialization flow from a completely clean state (checkpoint 9c595bc9b42d). Simply deleting `.reflect/` is insufficient; the qmd collection must be cleaned separately.

## Context

The qmd collection uses the naming convention `reflect-<repo-name>` to avoid collisions across multiple repos. This independence is by design — qmd collections are project-scoped artifacts that persist across sessions. However, this also means they require explicit cleanup if you want to reset state completely.
