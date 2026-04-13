---
created: 2026-04-13
updated: 2026-04-13
sources: [checkpoint bdd0e5492e95, checkpoint b2a5adf63dd2, checkpoint 9c595bc9b42d, commit 5046a70, commit ec9047b]
tags: [qmd, performance, llama.cpp]
status: active
---

# Add Prebuilt llama.cpp Binary or Build Caching

## Problem

First-run qmd embed operations compile `llama.cpp` from source, blocking test execution for **5–10 minutes** (checkpoint bdd0e5492e95). This prevents completion of test validation workflows and severely degrades UX during `reflect init`.

### Specific Friction Points

- **Test blockage**: qmd embed cannot proceed until compilation finishes. The full test suite (`reflect ingest --verbose` with new triage/categories/qmd reindex) has never completed due to compile wait times (checkpoint b2a5adf63dd2)
- **Duplicate builds**: When no prebuilt GPU binary is available, `node-llama-cpp` spawns an independent llama.cpp build per invocation. Concurrent qmd processes each compile separately, doubling wasted effort (checkpoint bdd0e5492e95)
- **Silent platform confusion**: node-llama-cpp auto-selects the Vulkan prebuilt over the CPU-only prebuilt when both exist, then fails to compile from source if Vulkan SDK is missing. One session spent **11 minutes debugging** this opaque failure path before discovering the root cause (checkpoint 9c595bc9b42d)

## Current Mitigations

- Longer timeouts and visible progress indicators added to improve responsiveness (commit ec9047b)
- `reflect init` fixed to trigger qmd embed for pre-populated wikis (commit 5046a70)

Neither mitigates the underlying 5–10 minute compile delay.

## Options

1. **Prebuilt binary**: Ship llama.cpp binaries for x64, Vulkan GPU, and ARM targets; instant first-run, best UX, higher maintenance and distribution cost
2. **Build cache**: Cache compiled artifacts in `.cache/llama-cpp/` or similar; only first environment per machine pays compile cost, smaller distribution footprint
3. **CPU-only default**: Ensure CPU prebuilt is preferred over Vulkan; removes silent failures and confusing error paths, does not eliminate compile delay

## Why This Matters

Users perceive the tool as hung when `reflect init` or `reflect ingest` hits the 10-minute compile. Initialization feels broken. Test velocity is crippled. The full reflect → ingest → qmd query workflow cannot complete in a single session without waiting for two independent embed operations.
