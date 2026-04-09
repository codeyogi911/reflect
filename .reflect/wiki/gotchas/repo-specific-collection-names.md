---
created: 2026-04-09
updated: 2026-04-09
sources: [commit 7b17590, commit 1be188b, commit 2f5ad53]
tags: [multi-repo, collections, naming]
status: active
---

# Repo-Specific Collection Names Prevent Collisions

## The Problem

When multiple repositories use reflect in a shared environment (monorepo, local dev machine, or shared CI runners), QMD collections with identical names will collide. Two separate projects, each with their own `.reflect/` directory, might both create a collection named `docs` or `codebase`. Without namespacing, evidence from different repos mixes in the same collection, causing cross-contamination during ingestion, search, and wiki compounding.

## The Solution

Reflect applies a repo-identifier prefix to all QMD collection names (commit 7b17590). This ensures each repository's collections are namespaced uniquely: `project-a/docs` vs. `project-b/docs`, keeping evidence strictly isolated.

This is critical for workflows relying on persistent collection state:
- **High-water mark tracking** (commit 2f5ad53): incremental ingestion must not conflict across repos; if two repos wrote to the same collection, already-ingested evidence would be incorrectly re-marked
- **Wiki layer** (commit 1be188b): compounding knowledge must draw only from the correct repo's collected evidence, not leaked evidence from parallel runs

## When This Matters

**Monorepos**: multiple services or components may each run reflect agents; collections must be scoped per service to avoid mixing evidence.

**Local dev machines**: a developer working on multiple projects simultaneously will have separate `.reflect/` directories; QMD engines must not cross-pollinate collections between them.

**Parallel CI/CD**: test runs or deployments across repos executing concurrently must maintain isolated collection state. Without repo-specific names, concurrent writes to the same collection cause race conditions and data loss.

## Implementation Detail

The repo identifier (typically derived from the repo slug or hash) prefixes every collection name before it reaches the QMD backend. All subsequent operations—ingestion, search, wiki compounding—work within the scoped namespace transparently.
