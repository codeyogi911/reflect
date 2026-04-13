---
created: 2026-04-13
updated: 2026-04-13
sources: [checkpoint b2a5adf63dd2, checkpoint bdd0e5492e95, checkpoint 9c595bc9b42d, checkpoint 4ecb34b81a12]
tags: [testing, qmd-integration, v1.0.0-refactor]
status: active
---

# Validate Full 1-2-3 Test Sequence End-to-End

The reflect v1.0.0 knowledge-base refactor introduced agentic flag integration (checkpoint b2a5adf63dd2), dynamic wiki categories, and qmd-driven semantic search (checkpoint 4ecb34b81a12), but the comprehensive three-part test validating all components in sequence has never completed successfully.

## The 1-2-3 Test Sequence

**Test 1: qmd Semantic Query with Agentic Flags**  
Execute a query against the reflect wiki using qmd's agentic interface (--json, --files, --min-score, --full). Verify ranked structured output is returned and suitable for agent consumption. This test confirms qmd has completed vector embedding.

**Test 2: reflect ingest with New Triage & Dynamic Categories**  
Run `reflect ingest --verbose` on existing evidence. Validate:
- Broader triage subagent extracts all knowledge types (brand, preferences, patterns, business decisions, corrections) (checkpoint 4ecb34b81a12)
- Dynamic category directories created on-the-fly without hardcoded list
- qmd auto-reindex (update + embed) completes without stalling
- Wiki index.md generated with active pages only

**Test 3: Keeper Agent Evidence Ladder Integration**  
Confirm keeper agent retrieves evidence using the new priority order: qmd query first (fast), then full session search, then git history. Validates the agentic flags are wired correctly through skill/agents (checkpoint b2a5adf63dd2).

## Why Test Never Completed

Multiple blockers prevented end-to-end validation:

- **First-run llama.cpp compilation**: qmd compiles llama.cpp from source on first use with no prebuilt binary, blocking all queries for 5–10 minutes with invisible progress (checkpoint bdd0e5492e95, 9c595bc9b42d)
- **qmd embed stalling**: `reflect ingest` halted indefinitely on evidence gathering when CLI was slow; kill-and-retry proved more reliable than waiting (checkpoint 9c595bc9b42d)
- **Output piping masks progress**: Using `tail -30` buffered output silently until completion, making the process appear hung (checkpoint 9c595bc9b42d)
- **Environment auto-selection**: node-llama-cpp auto-selects Vulkan prebuilt over CPU-only, then fails without Vulkan SDK present (checkpoint 9c595bc9b42d)

## Success Criteria

- [ ] Test 1: qmd query returns structured ranked hits with --json flag, agentic flags working
- [ ] Test 2: `reflect ingest --verbose` completes with dynamic categories, qmd reindex succeeds, index.md generated
- [ ] Test 3: keeper agent retrieves from qmd first with correct fallback chain
- [ ] All three tests run sequentially in a clean environment (CPU-only or verified GPU)
- [ ] No stalled processes, uncommitted changes committed before session end

## Environment Checklist

- Remove Vulkan SDK or explicitly install CPU-only prebuilt to force llama.cpp path
- Allow 10+ minutes for first-run qmd embed; monitor logs directly without piping
- Kill stray `reflect ingest` or qmd background processes before retry
- Verify `.gitignore` excludes transient artifacts (e.g., `wiki.bak`) to keep working tree clean
