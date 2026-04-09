---
created: 2026-04-07
updated: 2026-04-09
sources: [commit 2f5ad53, commit 1be188b, commit 7b17590]
tags: [incremental-ingest, persistence, session-chaining, performance]
status: active
---

# High-Water Mark Tracking for Incremental Ingest

## Overview

High-water mark tracking is a checkpoint-based mechanism that prevents redundant processing when ingesting repository evidence across multiple sessions. Rather than re-scanning and re-processing identical code or checkpoints on each session start, the system records the last successfully processed state and resumes from that point on subsequent runs.

## Why It Matters

Without high-water mark tracking, each session would re-index all repository content, redundantly extract evidence, and recompute knowledge artifacts. This creates two problems: wasted computational effort and stale or duplicative knowledge in the wiki layer. High-water mark tracking (commit 2f5ad53) solves this by enabling **incremental, stateful ingest** — only new commits, modified files, or novel checkpoints are processed and merged into the persistent knowledge base.

## Mechanism

The high-water mark approach records the ID or timestamp of the last successfully ingested item (commit, checkpoint, or collection batch). On the next session, the ingest pipeline queries from that mark onward, filtering out already-processed content. This is particularly important for repo-specific metadata: commit 7b17590 introduced repo-specific qmd (query metadata) collection names to avoid collisions across projects, meaning the high-water mark must also be scoped per repository.

## Integration with Wiki Layer

The wiki layer (commit 1be188b, v0.6.0) provides the persistent storage for compounding knowledge. High-water mark tracking ensures that sessions don't just accumulate redundant facts — they add incremental, novel insights. When a new commit is ingested, its evidence contributes fresh context to the wiki; older commits are skipped entirely, reducing memory overhead and search noise.

## Session Chaining Benefit

This mechanism directly enables session chaining: because state is tracked across sessions, an agent can run multiple focused tasks in sequence without losing accumulated context. Commits 04dd4dd and 33f3add document session chaining guidance; high-water mark tracking is the underlying infrastructure that makes this efficient rather than wasteful.
