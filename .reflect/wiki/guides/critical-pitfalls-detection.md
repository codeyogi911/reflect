---
created: 2026-04-13
updated: 2026-04-13
sources: [checkpoint 9c595bc9b42d, checkpoint b2a5adf63dd2, checkpoint bdd0e5492e95, commit 9cdf813]
tags: [triage, knowledge-extraction, gotchas]
status: active
related: [decisions/critical-pitfalls-detection, gotchas/repo-specific-collection-names, gotchas/symlink-hooks-directory]
---

# Critical Pitfalls Detection in Triage

Critical pitfalls are gotchas, design traps, and silent failures discovered during work that could block or confuse future developers. The triage subagent extracts these signals from session evidence during ingest to prevent repeated mistakes and surface hidden assumptions.

## What Counts as a Critical Pitfall

A pitfall is actionable when it involves:

- **Silent failures**: Code that runs without error but produces wrong results (e.g., search.py using `--limit` instead of qmd's correct `-n` flag) (checkpoint b2a5adf63dd2)
- **Environment-specific gotchas**: Implicit package conflicts or runtime assumptions (e.g., node-llama-cpp auto-selecting Vulkan prebuilt over CPU-only when both installed, then failing silently with no Vulkan SDK) (checkpoint 9c595bc9b42d)
- **Workflow friction**: Processes that mask progress or cause deadlock (e.g., piping long-running CLI output through `tail -30` buffers everything until completion, making progress invisible) (checkpoint 9c595bc9b42d)
- **State management traps**: Implicit cleanup or ordering requirements (e.g., stale qmd collections retain broken path references after wiping `.reflect/` and must be explicitly removed) (checkpoint 9c595bc9b42d)
- **Implicit assumptions**: Design decisions not documented that fail at runtime (e.g., `reflect init` silently skips qmd embed for pre-populated wikis, forcing manual discovery) (checkpoint bdd0e5492e95)

## Detection Patterns

The triage subagent scans checkpoint evidence for these signals:

- **"Friction:" sections** in checkpoint outcomes — lists real-world pain points, blocked work, and wasted time
- **"Learnings:" subsections tagged "Gotcha"** — specific traps and corner cases
- **"Open Items:" marked as blockers** — critical gaps that impeded progress
- **Latent bugs mentioned mid-session** — runtime failures discovered only after implementation
- **Repeated pain across checkpoints** — same issue appearing in multiple sessions (e.g., llama.cpp compile blocking on first-run, appearing in checkpoints bdd0e5492e95 and 9c595bc9b42d)

## Examples from Recent Session

From the v1.0.0 rebuild session (checkpoint 9c595bc9b42d), extracted pitfalls include:

- Vulkan prebuilt auto-selection masking CPU-only path, then failing without Vulkan SDK present
- qmd collections persisting with broken references after `.reflect/` directory wipe
- Output piping through `tail` silencing progress indefinitely
- Concurrent qmd processes each triggering duplicate llama.cpp compilations
- The `.gitignore` requirement for transient test artifacts to keep working tree clean

## Why This Matters

Pitfalls are more actionable than generic learnings — they prevent the next developer from losing hours to environment setup, silent bugs, or workflow friction. By extracting them explicitly during triage, the knowledge base surfaces hidden costs and design assumptions that would otherwise remain tacit.
