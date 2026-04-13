---
created: 2026-04-13
updated: 2026-04-13
sources: [checkpoint 4ecb34b81a12, checkpoint 9c595bc9b42d]
tags: [wiki-maintenance, index-management, archiving]
status: active
---

# Wiki Archiving and Index Bounded Growth

Prevent unbounded wiki index growth by archiving stale pages, removing resolved items, and merging duplicates. The pattern keeps the wiki index lean and queryable by ensuring `index.md` reflects only active knowledge.

## The Pattern

When ingesting sessions and updating the wiki, three types of cleanup occur (checkpoint 4ecb34b81a12):

1. **Stale pages** → move to `_archive/` directory  
2. **Resolved items** (closed decisions, completed tasks) → remove from active index  
3. **Duplicates** → merge into a single canonical page  

After cleanup, `update_index_md()` regenerates a committed, human/LLM-readable table of contents showing only active pages.

## Why It Matters

Without bounded growth, the wiki index becomes a dumping ground: resolved decisions clutter active decisions, outdated patterns obscure current best practices, and query results dilute with noise. A lean index keeps knowledge discoverable and agents focused on actionable information.

## Implementation

In `lib/wiki.py`, the `update_index_md()` function is the enforcement point. It generates the index.md file to include only pages that are not marked as archived or resolved. This index becomes the source of truth for what agents and humans consider "active knowledge" (checkpoint 4ecb34b81a12).

The `_archive/` directory is a first-class location within the wiki structure. Pages moved there are preserved for historical reference but excluded from semantic queries and active index listings.

## When to Apply

Run linting and archival:
- After major ingest cycles that consolidate many related sessions  
- During quarterly maintenance sweeps of the wiki  
- When duplicate or superseded pages are discovered during review  

Related: After archiving pages or wiping `.reflect/` state, explicitly remove stale qmd collections to avoid broken path references in the search index (checkpoint 9c595bc9b42d).
