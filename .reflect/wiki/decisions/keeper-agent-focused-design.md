---
created: 2026-04-09
updated: 2026-04-09
sources:
  - commit 34626f0
  - commit fd5f2a2
  - commit 0500d79
  - commit 1be188b
  - commit 2f5ad53
  - commit 7b17590
tags: [keeper-agent, memory-scope, architecture, decisions]
status: active
---

# Keeper Agent: Focused Repo Memory

The Keeper Agent evolved from a **broad repo memory** approach to a **focused** one, deliberately narrowing its scope to deliver higher-signal knowledge that agents can reliably act on. This shift emerged after testing revealed that comprehensive tracking produces stale, unfocused artifacts.

## The Pivot: From Breadth to Depth

Keeper was initially rewritten as a broad repository chronicler (commit 34626f0), attempting to track all state changes and generate comprehensive summaries. However, practical testing showed this approach generated low-signal noise—agents struggled to distinguish critical insights from routine updates.

The refined Keeper agent (commit fd5f2a2) instead constrains its mandate to **high-impact, decision-driven knowledge**: architecture decisions, critical pitfalls, session learnings, and evidence snapshots. Generic file inventories and broad summaries were traded for focused depth.

## Implementation: Incremental and Scoped

The focused design leverages several technical patterns:

- **Incremental ingestion** with high-water mark tracking (commit 2f5ad53) prevents duplicate work across sessions, allowing Keeper to resume where it left off
- **Persistent wiki compilation** (commit 1be188b) transforms evidence into indexed markdown pages that compound knowledge over time
- **Critical pitfall detection** surfaces hard blockers early in the context pipeline (related to commit 0500d79)
- **Repo-specific namespacing** via MongoDB collection names (commit 7b17590) isolates data across multi-project setups, avoiding collisions

## What "Focused" Means

Rather than attempting to be a universal repository chronicle, Keeper now functions as a **scoped memory layer**:

1. **Selective ingestion**: captures only patterns with lasting impact or cross-session relevance
2. **Low maintenance overhead**: incremental state tracking eliminates reprocessing
3. **Compounded learning**: wiki pages persist and grow richer across sessions
4. **Decision-centric**: prioritizes actionable insights over comprehensive documentation

This focused scope makes Keeper maintainable, reliable, and genuinely useful to consuming agents—a decision log rather than an encyclopedia.
