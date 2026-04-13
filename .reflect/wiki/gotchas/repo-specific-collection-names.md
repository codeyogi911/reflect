---
created: 2026-04-13
updated: 2026-04-13
sources: [checkpoint 4ecb34b81a12, checkpoint 9c595bc9b42d, commit 53c09c4]
tags: [qmd, collections, naming, multi-repo]
status: active
---

# Repo-Specific Collection Names Required

qmd collections must follow the `reflect-<repo-name>` naming convention to isolate knowledge across multiple repositories on the same machine. (checkpoint 4ecb34b81a12)

## Why This Matters

When you initialize reflect on a repository with `reflect init`, it registers a qmd collection named `reflect-<repo-name>`. Each repository gets its own isolated collection so queries don't accidentally cross repo boundaries. If you attempt to use a generic or ambiguous collection name across multiple repos, you risk knowledge from one repository bleeding into queries for another, incorrect semantic search results due to mixed context, and confusion about which wiki pages belong to which repo.

## The Gotcha

The naming convention is **not optional** — it's baked into reflect's initialization and query logic. When you run `reflect init`, the tool automatically registers the collection as `reflect-<repo-name>` where `<repo-name>` is derived from your repository's directory or git remote.

**Critical**: When wiping `.reflect/` state (e.g., during testing or recovery), you must also explicitly remove the stale qmd collection. Simply deleting `.reflect/` leaves the qmd collection registered with broken path references, which will cause subsequent ingest operations to fail. (checkpoint 9c595bc9b42d)

## Cleanup

If you wipe `.reflect/` manually, clean up qmd collections before re-initializing:

```bash
qmd rm reflect-<repo-name>
```

This removes the stale collection registration so `reflect init` can register a fresh one with correct paths.
