---
created: 2026-04-13
updated: 2026-04-13
sources: [checkpoint b2a5adf63dd2, checkpoint 4ecb34b81a12, commit 9d724e8]
tags: [keeper, qmd, search, architecture]
status: active
related: [decisions/wiki-layer-persistent-knowledge.md, decisions/keeper-agent-focused-design.md]
---

# Keeper Agent Evidence Ladder: qmd First

The keeper agent's evidence retrieval hierarchy now prioritizes qmd-indexed wiki queries as the **fastest and primary rung**, falling back to session history and git commits only when qmd yields insufficient results (checkpoint b2a5adf63dd2).

## Decision

Use **qmd as the first rung** of the keeper agent's evidence ladder before descending to full session search or git history traversal.

## Rationale

qmd query is orders of magnitude faster than iterating through session transcripts or git logs because:
- **Indexed retrieval**: qmd maintains a BM25 full-text index plus vector embeddings built from wiki pages, enabling sub-second ranked hits
- **Semantic search**: Vector embeddings (powered by local llama.cpp) capture meaning beyond keyword matching, returning higher-quality results for ambiguous queries
- **Structured output**: qmd's `--json` flag surfaces ranked hits with scores, `--files` returns only paths above relevance threshold, and `--full` retrieves complete document content — all suitable for LLM consumption without parsing plain text
- **Bounded scope**: The keeper queries a curated wiki (not raw sessions), so results are already synthesized and deduplicated

## Evidence Ladder Order

1. **qmd collection query** (reflect-<repo>): Semantic + full-text search across indexed wiki pages
2. **Session history search**: grep-based checkpoint and transcript fallback if wiki lacks coverage
3. **Git log search**: Commit messages and diffs for historical context or version-specific changes

## Implementation

The keeper agent (`.claude/skills/reflect/agents/keeper.md`) was updated to query qmd before broader session/git search (checkpoint b2a5adf63dd2). This decision is part of the v1.0.0 architectural shift from context.md injection to agents self-serving via structured queries (checkpoint 4ecb34b81a12).

The qmd skill is auto-installed during `reflect init` with the collection named `reflect-<repo-name>`, and the wiki is re-indexed after every `reflect ingest` via `qmd update` + `qmd embed` operations.
