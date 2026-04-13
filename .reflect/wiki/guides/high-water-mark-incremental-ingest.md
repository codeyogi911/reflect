---
created: 2026-04-13
updated: 2026-04-13
sources: [checkpoint a835bc7b84e5, checkpoint 4ecb34b81a12]
tags: [ingest, performance, scaling]
status: active
related: [decisions/high-water-mark-incremental-ingest]
---

# High-Water-Mark Incremental Ingest Strategy

## Overview

The high-water-mark incremental ingest strategy tracks the latest successfully ingested checkpoint ID, ensuring each session evidence is examined exactly once during subsequent ingest runs. This pattern prevents re-processing of historical sessions as a repository accumulates evidence, keeping ingest time linear with new checkpoints rather than exponential with total project history (checkpoint a835bc7b84e5, checkpoint 4ecb34b81a12).

## The Problem

Without checkpoint tracking, `reflect ingest` would potentially re-examine all previous session evidence. In a mature repository with hundreds of sessions, ingest cost compounds: run 1 processes 10 sessions, run 2 re-processes those 10 plus 10 new ones (20 total), run 3 processes 30, and so on. The triage subagent would re-extract and re-categorize identical knowledge repeatedly, while qmd would re-embed pages that haven't changed, wasting CPU and wall-clock time.

## Implementation in Reflect v1.0.0

The high-water-mark is implemented within reflect's ingest pipeline (checkpoint 4ecb34b81a12) as part of the broader v1.0.0 knowledge base architecture:

- **Mark Persistence**: The checkpoint ID of the last successfully ingested evidence is recorded in `.reflect/` state, allowing the process to resume from the exact boundary across invocations.
- **Selective Triage**: The ingest triage subagent receives only checkpoint evidence *newer than the mark*, extracting brand guidelines, preferences, patterns, and business decisions from fresh sessions only.
- **Dynamic Categories**: New wiki categories are proposed and created only for new knowledge; existing categories are not re-evaluated for every ingest run.
- **Bounded Re-indexing**: After ingestion, `_qmd_reindex` runs `qmd update` (instant BM25 refresh) and `qmd embed` (slower vector indexing) on the modified wiki state, not a full re-index.

## Guarantees

1. **Single-Pass Processing**: Each checkpoint is examined exactly once; once ingested and committed, it is never re-processed.
2. **Linear Scaling**: Ingest time is proportional to *new* checkpoints, not total project history. A 6-month-old repo with 50 archived sessions ingests 1 new session in constant time.
3. **Wiki Convergence**: The wiki state remains consistent; stale pages are archived via lint, and re-indexed qmd reflects current knowledge only.

## When to Apply

Use this pattern for projects that:
- Conduct multiple Claude sessions incrementally over weeks or months
- Build a compounding wiki from session evidence
- Run `reflect ingest` regularly (daily or weekly)
- Expect hundreds of sessions before project completion

For one-off or ephemeral projects, a simple full-ingest (no mark tracking) is acceptable. High-water-mark becomes critical once ingest frequency × session count reaches a point where redundant re-triage becomes noticeable overhead.
