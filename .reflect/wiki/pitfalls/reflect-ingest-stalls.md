---
created: 2026-04-13
updated: 2026-04-13
sources: [checkpoint 9c595bc9b42d, checkpoint c960454549ca]
tags: [ingest, stalling, timeout, performance]
status: active
related: [decisions/high-water-mark-incremental-ingest.md]
---

# reflect ingest Can Stall on Evidence Gathering

When running `reflect ingest` with a slow CLI environment, the ingest process can hang indefinitely during the evidence-gathering phase and never complete. This pitfall was encountered during the v1.0.0 init/ingest test cycle on CPU-only hardware (checkpoint 9c595bc9b42d).

## Symptoms

- `reflect ingest --verbose` begins normally but halts mid-run with no error message
- The process consumes minimal CPU/memory, suggesting it is blocked waiting for I/O or a subprocess
- The hang occurs specifically during the evidence-gathering step (before triage, wiki writing, or qmd re-indexing)
- Waiting does not resolve the issue; the process will remain hung indefinitely

## Root Cause

The ingest pipeline spawns CLI subprocesses (likely qmd queries or git operations) to collect evidence for the triage agent. When the CLI is slow—such as on CPU-only systems performing the first-run llama.cpp compilation—these subprocesses can become very slow. The parent ingest process does not implement a timeout or cancellation mechanism, so it waits indefinitely for the subprocess to return.

## Current Mitigation

Kill the hung ingest process and retry. This is more reliable than waiting, especially in resource-constrained environments (checkpoint 9c595bc9b42d). If using a shell wrapper (e.g., bash piping through `tail`), note that the wrapper may remain hung even after the underlying node process is killed, requiring a separate kill step.

## Proposed Solutions

Two approaches are under investigation (checkpoint 9c595bc9b42d):

1. **Timeout mechanism**: Add explicit timeouts to evidence-gathering subprocesses so ingest fails fast and can be retried rather than hanging indefinitely.
2. **Chunking strategy**: Batch evidence collection into smaller, faster rounds with intermediate checkpoints, allowing partial ingests to succeed even if later batches are slow.

A partial solution was applied to qmd embed ergonomics (checkpoint c960454549ca: "longer timeout, visible progress, GPU hint"), but the root evidence-gathering stall has not been fully resolved.

## Avoidance

- Run `reflect ingest` on systems with prebuilt GPU binaries or cached llama.cpp builds to keep CLI latency low
- Monitor the ingest process with verbose output to detect hangs early
- Use background/concurrent execution with timeout wrappers if integrating ingest into CI/automation
