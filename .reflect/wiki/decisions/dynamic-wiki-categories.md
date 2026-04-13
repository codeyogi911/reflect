---
created: 2026-04-13
updated: 2026-04-13
sources: [checkpoint 4ecb34b81a12, checkpoint a835bc7b84e5]
tags: [wiki-architecture, categories, triage, v1.0.0]
status: active
---

# Dynamic Wiki Categories (v1.0.0)

## Previous Model (Hardcoded)

Prior to v1.0.0, the wiki used four fixed categories: `decisions/`, `gotchas/`, `patterns/`, and `learn/`. All pages were manually routed into these predetermined buckets regardless of actual content type or domain. This rigid structure limited the ability to capture and organize domain-specific knowledge (brand guidelines, business rules, architectural patterns, code preferences, etc.).

## New Model (Dynamic)

Starting with v1.0.0, wiki categories are **proposed dynamically by the triage subagent** during the ingest phase (checkpoint 4ecb34b81a12). Instead of injecting knowledge into fixed categories, the triage prompt was rewritten to extract ALL knowledge types — brand, preferences, patterns, business decisions, critical pitfalls, technical constraints, and more. New category directories are created on the fly in `lib/ingest.py` as the triage subagent proposes them.

## Rationale

The hardcoded categories reflected only session-level signals (decisions, gotchas, patterns, learnings). The broader ingest triage prompt enables the system to recognize and organize knowledge at a higher level of abstraction: *what the knowledge is* rather than *where it was uttered*. This aligns with the v1.0.0 principle that "sessions are the sole source of truth" — every decision, preference, brand guideline, and correction flows through session evidence, and the triage stage now extracts and organizes that evidence semantically rather than syntactically (checkpoint 4ecb34b81a12).

## Implementation

The dynamic category creation logic lives in `lib/ingest.py` and is paired with the new qmd-backed retrieval model: agents self-serve via qmd queries rather than relying on pre-computed context.md injection. Index growth is bounded by lint rules — stale pages archive to `_archive/`, resolved items move out, duplicates merge — ensuring the index reflects only active pages (checkpoint 4ecb34b81a12).

## Boundary

When triage proposes a category, a new directory is created if it does not exist. All proposed pages flow into their assigned categories. The system is backward-compatible: existing hardcoded categories (`decisions/`, `gotchas/`, etc.) continue to work; new categories emerge organically from content.
