---
created: 2026-04-13
updated: 2026-04-13
sources: [checkpoint b2a5adf63dd2, commit 9d724e8]
tags: [qmd, query-grammar, search]
status: active
---

# qmd Advanced Query Grammar Prefixes

qmd supports four advanced query grammar prefixes—**lex:**, **vec:**, **hyde:**, and **intent:**—for use when the default hybrid search strategy is insufficient (checkpoint b2a5adf63dd2).

## The Prefixes

- **lex:** — Lexical search using keyword-based matching (BM25)
- **vec:** — Vector search using semantic embeddings
- **hyde:** — Hypothetical Document Embeddings; synthetic document generation for improved retrieval
- **intent:** — Intent-based search; semantic interpretation of query intent

## When to Use

By default, qmd combines multiple retrieval signals in a hybrid approach. When this hybrid strategy produces suboptimal results, these prefixes allow explicit control over which retrieval mechanism dominates:

- Use **lex:** when keyword precision or exact terminology is critical
- Use **vec:** when semantic similarity and conceptual relationships matter most
- Use **hyde:** when queries use indirect or exploratory phrasing
- Use **intent:** when the query's underlying semantic intent differs significantly from literal wording

## Integration with reflect

In the reflect keeper agent's evidence ladder, qmd queries form the first and fastest retrieval rung before descending to broader session or git history search. Advanced prefixes support precise knowledge lookups when the default hybrid search fails to surface needed information (checkpoint b2a5adf63dd2).

These prefixes work with qmd's five query types (`query`, `search`, `vsearch`, `get`, `multi-get`) and agentic output flags (`--json`, `--files`, `--min-score`, `--full`, etc.), enabling agents to construct retrieval-specific queries for knowledge base lookups with structured output.
