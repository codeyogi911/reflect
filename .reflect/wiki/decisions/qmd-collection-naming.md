---
created: 2026-04-13
updated: 2026-04-13
sources: [checkpoint 4ecb34b81a12, checkpoint 9c595bc9b42d, checkpoint bdd0e5492e95]
tags: [qmd, naming, collections, init]
status: active
related: [gotchas/repo-specific-collection-names]
---

# qmd Collection Naming: reflect-<repo-name>

## The Decision

Each repository's qmd collection must be named using the pattern `reflect-<repo-name>` where `<repo-name>` is derived from the repository's directory name or git config. (checkpoint 4ecb34b81a12)

## Problem Solved

Without a repo-specific suffix, two different projects on the same machine could both try to register a qmd collection named simply `reflect`, causing a collision that loses indexed knowledge or corrupts the index. By making the collection name unique per repo using `reflect-<repo-name>`, each repository can safely coexist with its own independent knowledge index on the same machine without interference. (checkpoint 4ecb34b81a12)

## Implementation

The naming and registration happen automatically during `reflect init` in `lib/init.py`. The flow:
1. Auto-installs qmd if needed
2. Extracts the repository name from directory or git config
3. Registers the qmd collection as `reflect-<repo-name>`
4. Seeds embeddings from existing wiki pages (checkpoint bdd0e5492e95)

The init operation is idempotent and can be re-run safely without re-registering or corrupting the collection. (checkpoint 4ecb34b81a12)

## Critical Caveat

Stale qmd collections must be manually removed if you wipe `.reflect/` state. The collection registration and directory state are independent — wiping one does not clean up the other. Always remove both the `.reflect/` directory and the associated qmd collection together to avoid broken path references in subsequent re-initialization. (checkpoint 9c595bc9b42d)
