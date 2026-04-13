---
created: 2026-04-13
updated: 2026-04-13
sources: [checkpoint bdd0e5492e95]
tags: [qmd, llama.cpp, concurrency]
status: active
---

# Concurrent qmd Processes Trigger Duplicate Builds

Multiple simultaneous `qmd` invocations each spawn independent `llama.cpp` compilations if no prebuilt binary exists, exponentially multiplying build time and system load.

## The Problem

When `qmd` runs for the first time without a prebuilt `llama.cpp` binary, it compiles from source. If multiple `qmd` processes start concurrently—for example, two semantic search queries or an initial `qmd embed` alongside a background query—each process independently detects the missing binary and initiates a separate full compilation (checkpoint bdd0e5492e95). This results in doubled compile work and significantly delayed completion.

In practice: `reflect init` triggers an initial `qmd embed` while a background task has a pending `qmd` query. Both processes are unaware of each other; both kick off `llama.cpp` builds.

## When This Occurs

- During `reflect init` on a repo with existing wiki pages (triggering initial `qmd embed`)
- When `qmd` query or update operations are issued in rapid succession
- Background ingest tasks running concurrently with user-triggered commands
- Multi-agent workflows where the keeper agent and other tools call `qmd` in parallel

## Solution

**Kill excess background processes before the shared build step.** Once the first `qmd` process begins compiling `llama.cpp`, terminate any redundant pending `qmd` invocations. Subsequent processes will detect the compiled binary and skip re-compilation (checkpoint bdd0e5492e95).

Practical steps:
1. Monitor for multiple `qmd` or `node` processes: `ps aux | grep qmd` or `jobs -l`
2. Kill duplicates: `kill <pid>` for excess processes
3. Allow the first build to complete (5–10 minutes from source)
4. Resume operations once the binary exists

First-run `llama.cpp` compilation from source takes approximately 5–10 minutes with no prebuilt binary available.
