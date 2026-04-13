---
created: 2026-04-13
updated: 2026-04-13
sources: [checkpoint 4ecb34b81a12, checkpoint b2a5adf63dd2, checkpoint a835bc7b84e5]
tags: [architecture, knowledge-base, v1.0.0]
status: active
related: [decisions/wiki-layer-persistent-knowledge.md, decisions/zero-storage-architecture.md, decisions/keeper-agent-focused-design.md]
---

# Sessions as Source of Truth

**Decision**: All project knowledge flows exclusively through session transcripts and evidence (git history, code diffs, event logs). No external data adapters, API integrations, or side-channel knowledge sources are maintained.

## Rationale

The v1.0.0 architecture eliminates the complexity of syncing knowledge from multiple external sources (docs, Jira, Slack, environment configs) by treating **sessions as the canonical knowledge store**. Every decision, preference, brand guideline, bug workaround, and correction is captured when it appears in an AI coding session, then ingested into the wiki (checkpoint 4ecb34b81a12).

This means:
- No stale documentation problem — docs are generated from living session evidence
- No permission/access issues with external APIs
- No latency waiting for external systems to be queried
- No impedance mismatch between AI reasoning and stored knowledge

## What This Replaces

The v0 model used:
- Four hardcoded wiki categories (`decisions/`, `patterns/`, `gotchas/`, `references/`)
- A static `context.md` file injected into every agent's system prompt
- Manual extraction and categorization of knowledge

The v1.0.0 model uses:
- Dynamic wiki categories proposed by the triage subagent during ingest
- Agents query a semantic knowledge base (`qmd` collection) directly
- Automated broad-spectrum knowledge extraction across all types (decisions, preferences, brand, patterns, business logic, infrastructure gotchas)

## The Pattern: Reflect Writes, QMD Reads

Sessions → **Reflect ingests** → Wiki pages (git-tracked) → **QMD indexes** → Agents query

This separation of concerns allows (checkpoint 4ecb34b81a12):
- Reflect owns ingestion, triage, categorization, and wiki maintenance
- QMD owns semantic search and retrieval
- Agents never need injected context — they fetch what they need when they need it

No external adapters required: all evidence is already captured in session checkpoints and git history, which reflect processes into markdown pages and qmd indexes.
