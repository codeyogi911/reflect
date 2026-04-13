---
created: 2026-04-13
updated: 2026-04-13
status: active
---

---
created: 2026-04-13
updated: 2026-04-13
sources:
  - checkpoint a835bc7b84e5
  - checkpoint b2a5adf63dd2
  - checkpoint 4ecb34b81a12
  - checkpoint 9c595bc9b42d
  - commit fd5f2a2
tags:
  - keeper-agent
  - qmd
  - architecture
status: active
related:
  - decisions/wiki-layer-persistent-knowledge
  - decisions/zero-storage-architecture
  - gotchas/repo-specific-collection-names

# Keeper Agent: Focused Design

The Keeper Agent is a repo-memory agent that queries a qmd-indexed wiki using a three-tier evidence ladder. It prioritizes speed and precision by querying the indexed wiki first, then escalates to broader session search and git history only when necessary. (checkpoint a835bc7b84e5)

## Evidence Ladder

The keeper's query strategy follows a focused escalation pattern (checkpoint b2a5adf63dd2):

1. **Rung 1 (Fastest)**: qmd collection query against the indexed wiki. Returns ranked results in ~100ms after first run.
2. **Rung 2 (Broad Session)**: Full session checkpoint search across all recorded evidence when wiki results are insufficient.
3. **Rung 3 (Git Fallback)**: Git history search (commit messages, metadata) for project-wide context beyond recorded sessions.

qmd is promoted to the first rung because it's the fastest path to indexed wiki knowledge. (checkpoint b2a5adf63dd2)

## Agentic Query Interface

The keeper consumes structured qmd output via these agentic-specific flags (checkpoint b2a5adf63dd2):

- `--json`: Ranked hits in JSON format for LLM consumption
- `--files`: File paths above relevance threshold only
- `--min-score <float>`: Filter results by confidence score
- `--full`: Complete document content instead of snippets
- `-n <count>`: Result limit (correct flag; `--limit` causes silent failures)

## Advanced Query Grammar

qmd supports specialized search modes via query prefixes (checkpoint b2a5adf63dd2):

- `lex:<query>`: Lexical (BM25) search only
- `vec:<query>`: Vector (semantic) search only
- `hyde:<query>`: Hypothetical document embeddings
- `intent:<query>`: Intent-based retrieval

Default is hybrid search (BM25 + vector) unless explicitly prefixed.

## Self-Service Model

The keeper does not inject context into agent prompts. Instead, agents are told: "You have repo memory; query qmd collection `reflect-<repo-name>`." (checkpoint 4ecb34b81a12)

This separation of concerns means:
- Reflect owns ingestion, wiki maintenance, and qmd indexing
- Agents own retrieval and knowledge consumption
- Knowledge scope is not bounded by prompt injection limits

## Collection Naming

Each repo gets a collection named `reflect-<repo-name>` to prevent collisions across multiple projects. (checkpoint 4ecb34b81a12)

## Performance Characteristics

- qmd `update` (BM25 reindexing): instant
- qmd `embed` (vector embeddings): ~5-10 minutes first run (llama.cpp compilation); cached thereafter
- Typical query latency: ~100ms after first run
- llama.cpp prefers Vulkan GPU binaries; both must coexist or Vulkan SDK must be explicitly removed to force CPU-only execution (checkpoint 9c595bc9b42d)
