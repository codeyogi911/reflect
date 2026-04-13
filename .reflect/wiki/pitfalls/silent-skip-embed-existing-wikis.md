---
created: 2026-04-13
updated: 2026-04-13
sources: [checkpoint bdd0e5492e95, commit 5046a70, checkpoint 9c595bc9b42d, checkpoint 4ecb34b81a12]
tags: [qmd, init, embeddings]
status: resolved
---

# reflect init Silently Skips Embed for Existing Wikis (FIXED)

## The Bug

When running `reflect init` on a repository that already had pages in its wiki, the command would complete successfully but silently skip the qmd embedding step. This meant users would believe their wiki was fully initialized and queryable, but semantic search via qmd would fail or return empty results until they manually ran `qmd embed`. (checkpoint bdd0e5492e95)

The problem was invisible: no error was raised, no warning was printed — the init appeared to succeed, but the qmd index remained unsynchronized with wiki content.

## Root Cause

The init logic contained an empty-wiki guard to prevent wasting time embedding a fresh, unpopulated wiki during initial setup. However, the same guard also prevented embedding when the wiki *already had* pages from a previous run or migration, leaving the qmd index stale. (commit 5046a70)

This created an asymmetry: `reflect init` on a clean repo would result in a ready-to-query state, but `reflect init` on an existing repo would silently leave it in a broken state.

## The Fix

lib/init.py was updated to distinguish between two initialization scenarios: (commit 5046a70)

1. **Empty wiki (no pages)**: Skip embedding — nothing to index yet, user can ingest content later
2. **Pre-populated wiki (pages already exist)**: Trigger qmd embed — synchronize the index with existing content

This ensures `reflect init` is idempotent and always leaves the system in a fully queryable state, regardless of whether the wiki started empty or contained existing pages. (checkpoint 4ecb34b81a12)

## Current Behavior

Modern `reflect init` now:
- Installs and registers the qmd collection
- Skips embed if the wiki directory is empty
- **Triggers embed if pages already exist** (fixed behavior)
- Completes as a single idempotent operation with no manual embedding steps required afterward

The empty-wiki guard is preserved and tested; the fix adds the missing pre-populated case. (checkpoint 9c595bc9b42d)
