---
created: 2026-04-13
updated: 2026-04-13
sources: [checkpoint 4ecb34b81a12, checkpoint b2a5adf63dd2, commit 53c09c4]
tags: [architecture, separation-of-concerns, knowledge-base, qmd]
status: active
related: [decisions/wiki-layer-persistent-knowledge, decisions/keeper-agent-focused-design]
---

# Zero-Storage Architecture Principle

The zero-storage architecture establishes a clean separation of concerns: **Reflect owns ingestion; qmd owns retrieval**. No context is injected into the LLM context window. Instead, agents query the qmd knowledge base directly (checkpoint 4ecb34b81a12).

## Architecture

Reflect and qmd form a complementary pair:

- **Reflect** (writer): Owns ingestion, wiki maintenance, page curation, and index generation. Every session flows through `reflect ingest`, which updates the wiki and triggers re-indexing.
- **qmd** (reader): Owns retrieval, semantic search, ranking, and result serving. Agents query the `reflect-<repo>` collection directly via CLI or MCP server, receiving ranked hits suitable for LLM consumption.

The pattern is summarized as "Reflect writes, qmd reads" — a unidirectional flow with no injected context layer (checkpoint 4ecb34b81a12).

## Key Principle: Sessions as Source of Truth

Sessions are the sole source of truth. Every decision, preference, brand guideline, and correction flows through Entire CLI sessions into `reflect ingest`. No external source adapters are needed; the wiki grows purely from session evidence (checkpoint 4ecb34b81a12).

## Motivation

The previous model injected a static `context.md` file into the skill, forcing all agents to read the same pre-computed summary. This had three drawbacks:

1. **Stale knowledge**: Context updates lagged behind ingest; agents had outdated memory.
2. **No semantic retrieval**: Agents retrieved only what matched the fixed structure, not what was semantically relevant to their query.
3. **Context window waste**: Injecting megabytes of context consumed token budget even for irrelevant queries.

The zero-storage approach flips this: agents ask questions, qmd ranks relevant pages in real time, and the skill tells agents "query qmd collection `reflect-<repo>`" instead of "read this injected file" (checkpoint 4ecb34b81a12).

## Implementation

- **reflect init** auto-installs qmd via npm and registers the collection as `reflect-<repo>` (one per repo, idempotent).
- **reflect ingest** runs `qmd update` (BM25 index) and `qmd embed` (vector embeddings) after every wiki update, keeping retrieval indexes fresh.
- **Skill** documents only that agents have access to qmd; no context injection wiring.
- **Keeper agent** uses qmd as the first rung of its evidence ladder—fastest, most recent, most relevant (checkpoint b2a5adf63dd2).

## Evidence Ladder

With zero-storage, the keeper agent's evidence retrieval simplifies to a three-tier approach:

1. **qmd query** (fastest): Semantic search of indexed wiki.
2. **Session search**: Broader keyword search across session transcripts.
3. **Git history**: Commit log and code diffs.

qmd is promoted to the first rung because it's both fast and fresh (checkpoint b2a5adf63dd2); sessions and git are fallbacks for deeper context.
