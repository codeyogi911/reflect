---
created: 2026-04-13
updated: 2026-04-13
sources: [checkpoint b2a5adf63dd2, checkpoint 4ecb34b81a12]
tags: [qmd, query, agentic-flags, search]
status: active
related: [patterns/qmd-collection-naming, decisions/keeper-agent-focused-design]
---

# qmd Query Types and Agentic Flags

qmd ships with five distinct query types and a suite of agentic-specific CLI flags designed for AI agent consumption of structured, ranked search results (checkpoint b2a5adf63dd2).

## Query Types

qmd supports five query operations, each with its own semantics:

- **query** — Default hybrid search combining lexical and semantic matching
- **search** — Lexical/BM25-only search (fast, keyword-driven)
- **vsearch** — Vector-only search (semantic/embedding-driven)
- **get** — Direct document retrieval by path
- **multi-get** — Batch retrieval of multiple documents by path

Each type accepts agentic flags to shape output format and filtering behavior.

## Agentic Flags

The following flags enable structured, agent-optimized query response:

- **--json** — Output ranked hits as JSON-structured data suitable for LLM consumption instead of plain text
- **--files** — Return only file paths above a relevance floor (filtering metadata, returning paths only)
- **--min-score** — Threshold filter; exclude results below specified relevance score
- **--full** — Retrieve complete document content (instead of summaries or snippets)
- **-n** — Specify result count limit (e.g., `-n 5` for top 5 hits)
- **--no-rerank** — Skip the reranking step, returning raw embedding scores

These flags can be combined to customize response behavior. For example, `qmd query --json -n 5` returns the top 5 ranked results in JSON; `qmd query --files --min-score 0.7` returns only paths scoring above 0.7.

## Query Grammar Prefixes

For cases where the default hybrid behavior is insufficient, qmd supports grammar prefixes to route queries explicitly (checkpoint b2a5adf63dd2):

- **lex:** — Force lexical search only
- **vec:** — Force vector search only  
- **hyde:** — Use HyDE (hypothetical document embeddings) for enhanced semantic matching
- **intent:** — Parse query intent and route accordingly

For example, `qmd query "lex:database transactions"` bypasses semantic matching and performs pure keyword search.

## Integration with Reflect

The reflect project surfaces qmd agentic flags in keeper agent queries and skill documentation (checkpoint b2a5adf63dd2). The keeper agent uses qmd as the first rung of its evidence ladder, querying the `reflect-<repo-name>` collection before descending to broader session or git search. All agentic flags are documented as first-class examples in the reflect skill so downstream agents understand how to structure qmd queries for optimal results.
