---
created: 2026-04-13
updated: 2026-04-13
sources: [checkpoint 4ecb34b81a12, checkpoint 9c595bc9b42d]
tags: [wiki, archiving, lifecycle, index]
status: active
related: [decisions/wiki-layer-persistent-knowledge]
---

# Wiki Index Lifecycle and Archiving

The reflect wiki bounds its index growth by archiving stale pages, removing resolved items, and merging duplicates. This keeps the active knowledge base lean and prevents agents from querying outdated context (checkpoint 4ecb34b81a12).

## Archival Mechanism

Pages transition to `.reflect/wiki/_archive/` when they become stale or resolved:

- **Stale**: Pages with no updates after a staleness threshold
- **Resolved**: Completed decisions or investigations; marked complete but preserved for reference
- **Duplicate**: Merged into a single canonical page; the non-canonical version archived or removed

Relative paths are preserved during archival: `decisions/old-pattern.md` becomes `_archive/decisions/old-pattern.md`.

## Index Management

The `update_index_md()` function in `lib/wiki.py` generates a committed, human/LLM-readable table of contents showing **only active pages** (checkpoint 4ecb34b81a12). This index is the single source of truth for what the wiki contains—archived pages remain in the filesystem and are searchable via qmd but do not appear in the active catalog.

## qmd Re-indexing Lifecycle

After archival operations, `qmd update` and `qmd embed` refresh the search index. Stale qmd collections should be explicitly removed and re-registered after wiping `.reflect/` state; otherwise, path references to archived pages can become broken (checkpoint 9c595bc9b42d).

## Rationale

Bounding the active index prevents:
- **Agent confusion**: Outdated decisions or duplicate context appearing in search results
- **Cognitive overload**: Large, mixed-quality knowledge catalogs are slower to parse
- **False memories**: Stale patterns appearing alongside current best practices, creating conflicting guidance

Archive-not-delete preserves historical context for forensic searches and rare deep dives while maintaining a clean, current active state.
