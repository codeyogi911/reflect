---
created: 2026-04-13
updated: 2026-04-13
sources: [checkpoint 4ecb34b81a12, checkpoint b2a5adf63dd2, checkpoint bdd0e5492e95, checkpoint 9c595bc9b42d, checkpoint a835bc7b84e5]
tags: [wiki, knowledge-base, qmd, architecture]
status: active
related: [decisions/wiki-layer-persistent-knowledge.md, decisions/keeper-agent-focused-design.md]
---

# Wiki Layer: Persistent Knowledge Base

The wiki layer is reflect's persistent, long-lived knowledge base. It ingests session evidence into structured markdown pages organized by dynamic categories, then indexes them with qmd for semantic retrieval. The pattern is: **Reflect writes, qmd reads.** (checkpoint 4ecb34b81a12)

## Architecture

The wiki lives in `.reflect/wiki/` and is split into subdirectories by knowledge type:

- `decisions/` — architectural decisions, preferences, business rules
- `gotchas/` — pitfalls, failed approaches, anti-patterns
- `guides/` — how-to documentation, procedures
- `_archive/` — resolved or superseded pages (auto-managed by lint)
- `index.md` — human and LLM-readable table of contents (auto-generated)

Pages are created by the triage subagent during `reflect ingest`, which proposes dynamic categories based on session evidence. (checkpoint 4ecb34b81a12) Each page is committed independently, making the wiki a browsable git history of decisions and learnings.

## Indexing with qmd

The wiki is indexed with qmd, Anthropic's semantic search tool. After every `reflect ingest`, the system runs `qmd update` (instant BM25 reindex) followed by `qmd embed` (slower vector indexing). (checkpoint bdd0e5492e95)

Collections follow the convention `reflect-<repo-name>` to avoid collisions across multiple projects. (checkpoint 4ecb34b81a12) Agents query the collection directly via `qmd query` with structured flags like `--json`, `--files`, and `--full`. The keeper agent uses qmd as its first rung of the evidence ladder before descending to broader session search. (checkpoint b2a5adf63dd2)

## Page Lifecycle

Pages accumulate over time, but growth is bounded by lint rules:

- **Active pages** remain in their category and are indexed by qmd.
- **Resolved items** (status: resolved in YAML frontmatter) are moved to `_archive/` to keep the main index clean.
- **Duplicates** are merged; the preferred version is kept, others are retired.
- **Stale pages** older than the project's staleness threshold are archived.

The `index.md` file is auto-generated and committed after each ingest, showing only active pages with their tags and status. (checkpoint 4ecb34b81a12)

## Ingestion Flow

`reflect ingest` extracts all knowledge types from session evidence: decisions, preferences, patterns, brand guidelines, business rules, gotchas, and pitfalls. The triage subagent proposes category assignments on the fly. Each page receives:

- **YAML frontmatter:** created, updated, sources (checkpoint IDs), tags, status, related pages
- **Body:** specific facts, exact values, reasoning, no generic advice
- **Citations:** inline evidence references like `(checkpoint abc123)`

After all pages are written, `reflect init` is idempotent and automatically installs qmd via npm, registers the collection as `reflect-<repo-name>`, and skips context.md injection. (checkpoint 4ecb34b81a12) First-run qmd embed compiles llama.cpp from source and can take 5–10 minutes; subsequent runs are instant. (checkpoint bdd0e5492e95)

## Maintenance

If you wipe the `.reflect/` directory during testing or recovery, also explicitly remove the stale qmd collection — it retains broken path references that will cause queries to fail. (checkpoint 9c595bc9b42d)

The skill no longer injects context; instead, it tells agents: **"You have memory. Query qmd collection `reflect-<repo-name>` directly."** Agents own their evidence gathering, reducing bloat and keeping the skill minimal.
