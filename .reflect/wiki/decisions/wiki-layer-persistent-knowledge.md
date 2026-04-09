---
created: 2026-04-09
updated: 2026-04-09
sources: [commit 1be188b, commit 2f5ad53, commit 7b17590, commit 33f3add]
tags: [wiki, persistence, knowledge-accumulation, v0.6.0]
status: active
related: [decisions/keeper-agent-repo-memory, features/cross-session-learning]
---

# Wiki Layer for Persistent Compounding Knowledge

## Overview

The wiki layer (v0.6.0) introduces a structured mechanism for agents to build and reference persistent knowledge across sessions, extending the session-based evidence capture model established in earlier versions. Rather than treating knowledge as ephemeral checkpoints scoped to individual sessions, the wiki layer enables agents to compile, curate, and incrementally refine knowledge artifacts that compound over time (commit 1be188b).

## Problem Statement

Prior to v0.6.0, cross-session knowledge relied on checkpoint references within session logs. Agents could query past evidence but had no formal way to synthesize insights into evolving, canonical documents. This created friction when:
- Multiple agents need shared, authoritative facts about the repository
- Knowledge evolves through repeated refinement across sessions
- Agents must manually re-discover or re-synthesize insights from scattered checkpoints

## Architecture

The wiki layer uses **incremental ingest with high-water mark tracking** (commit 2f5ad53). Rather than re-processing all historical evidence on each session, agents maintain a pointer to the last processed checkpoint and only ingest new evidence since that point. This enables:

1. **Efficiency**: Avoid redundant processing of old sessions
2. **Idempotency**: Agents can safely re-run without duplicating prior work

To prevent collision across multiple repositories using the same centralized storage, the wiki uses **repo-specific QMD collection names** (commit 7b17590), qualifying each repository's knowledge artifacts by a stable repository identifier.

## Integration with Keeper Agent

The wiki layer complements the Keeper agent (repo memory agent). While Keeper operates within a single session to understand the current repository state, the wiki layer allows Keeper and other agents to deposit curated knowledge for future sessions to build upon. Cross-session learning enhancements (commit 33f3add) document how agents should use both mechanisms in concert.

## Key Distinctions

- **Checkpoints**: Session-scoped, event-driven evidence capture (existing)
- **Wiki**: Repository-scoped, agent-curated synthesis of patterns, decisions, and lessons (new)
- **High-water mark**: Enables incremental reads without re-processing history

The wiki layer deliberately separates the *collection* of facts (via checkpoints) from the *curation* of knowledge (via wiki articles), allowing human reviewers and agents to manage knowledge quality independently.
