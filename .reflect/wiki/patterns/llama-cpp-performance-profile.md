---
created: 2026-04-13
updated: 2026-04-13
sources: [checkpoint bdd0e5492e95, checkpoint b2a5adf63dd2, checkpoint 9c595bc9b42d, checkpoint c960454549ca]
tags: [qmd, performance, llama.cpp, indexing]
status: active
---

# llama.cpp Performance: Update vs Embed

## The Pattern

qmd's `update` (BM25 indexing) is **instant**, while `embed` (vector embedding) is **slow on first-run** due to llama.cpp compilation from source. This asymmetry is critical for knowledge base initialization workflows.

## Performance Characteristics

| Operation | First Run | Subsequent Runs | Cause |
|-----------|-----------|-----------------|-------|
| `qmd update` | Instant | Instant | Pure BM25 ranking; no external compilation |
| `qmd embed` | 5–10 minutes | Fast | First run triggers llama.cpp from-source compile |

First-run llama.cpp compilation from source typically takes **5–10 minutes** with no prebuilt GPU binary available (checkpoint bdd0e5492e95). Once compiled, the binary is cached and subsequent embed operations are fast.

## Why the Difference

qmd's `embed` operation requires llama.cpp to generate vector embeddings using a local LLM. On first invocation, if no prebuilt GPU binary (Vulkan, CUDA) is available, qmd spawns an llama.cpp build from source. This one-time compilation dominates the first embed run.

qmd's `update` operation is purely computational—BM25 ranking of indexed text—with no external compilation required.

## Practical Implications

**Initialization blocking**: reflect init runs both `qmd update` and `qmd embed` after ingesting wiki pages. The embed step blocks initialization for 5–10 minutes on first run, even though update finishes instantly (checkpoint bdd0e5492e95).

**Concurrent compilation waste**: If multiple qmd processes run concurrently without a prebuilt binary, each triggers its own llama.cpp build from source, **multiplying compile work**. Kill duplicate background processes before shared build steps (checkpoint bdd0e5492e95).

**GPU prebuilt conflicts**: node-llama-cpp auto-selects Vulkan over CPU-only when both are installed. If the Vulkan SDK is absent, compilation fails. Explicitly remove the Vulkan package to force CPU path (checkpoint 9c595bc9b42d).

## Workarounds

1. **Provide a prebuilt binary**: Reduces first-run embed to near-zero latency. Cache or distribute a prebuilt artifact.

2. **Increase timeout and show progress**: Embed operations need 60s+ timeouts and visible progress indication to avoid appearing hung (checkpoint b2a5adf63dd2, c960454549ca).

3. **Run update-only first**: For latency-critical workflows, run `qmd update` alone for rapid BM25 indexing, then defer `embed` to a background task.

4. **Separate and cache compilation**: Cache the llama.cpp build separately so it's never rebuilt across multiple qmd invocations in the same session.
