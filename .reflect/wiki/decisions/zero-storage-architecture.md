---
created: 2026-04-03
updated: 2026-04-09
sources: [commit 46c8781, commit 1be188b, commit 2f5ad53, commit 7b17590]
tags: [architecture, storage, harness, design]
status: active
related: [decisions/wiki-layer-v06, decisions/evidence-format-spec]
---

# Zero Storage Architecture (v4)

The Zero Storage Architecture (v4) is a foundational design pattern that eliminates external storage dependencies by storing all agent-generated evidence and metadata directly within the repository as first-class artifacts (commit 46c8781). This approach enables portable, agent-agnostic knowledge persistence without requiring separate databases, cloud services, or sidecar storage systems.

## Core Principle: Replaceable Harness

The "replaceable harness" pattern decouples the evidence format and schema from the runtime that generates it (commit 46c8781). The harness—any CLI, script, or agent framework that executes workflows—can be upgraded, swapped, or reimplemented entirely without breaking downstream consumers of the evidence. All information is serialized to stable formats (YAML checkpoints, structured metadata) that persist independently of the harness implementation.

This enables Claude or other agents to read evidence written by the current CLI, and future agents to read evidence written today, regardless of how the harness evolves.

## Storage Location and Structure

Evidence is stored in `.reflect/` directory at the repository root, organized as checkpoints and session metadata. Each session creates a timestamped record; each checkpoint captures execution state, reasoning, and outputs. By storing everything in the repo, the evidence benefits from version control, snapshots, and distributed access—the same mechanisms protecting source code now protect agent memory (commit 1be188b).

## Incremental Ingest and High-Water Marks

Later enhancements introduced high-water mark tracking (commit 2f5ad53) to enable efficient, incremental evidence collection across sessions. Rather than re-processing all historical checkpoints on every run, the system tracks which evidence has been ingested into the active knowledge layer. Repo-specific MongoDB collection names prevent collisions when multiple projects share a single embedding store (commit 7b17590).

## Why Zero Storage

- **Repo Portability**: Clone the repo, get all evidence immediately—no external sync required
- **Version Control Integration**: Evidence evolves with commits, enabling audit trails and recovery
- **No Infrastructure**: Works offline, in CI/CD, on local machines without cloud dependencies
- **Agent Agnostic**: Any tool reading `.reflect/` formats understands the evidence

This architecture is active and used as the foundation for cross-session learning, the wiki layer (v0.6.0), and ongoing memory management enhancements.
