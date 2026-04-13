---
created: 2026-04-13
updated: 2026-04-13
sources: [checkpoint 9c595bc9b42d, checkpoint c960454549ca, checkpoint bdd0e5492e95, commit ec9047b, commit 0839021]
tags: [ingest, performance, stall]
status: open
---

# Investigate reflect ingest Stalling on Evidence Gathering

## Problem

The `reflect ingest` command hangs indefinitely when gathering evidence if any downstream CLI operation is slow. This blocks the entire ingest pipeline and forces users to kill the process and retry manually (checkpoint 9c595bc9b42d).

## Current Behavior

When running `reflect ingest --verbose`:
- The command enters the evidence-gathering phase and appears to hang
- No timeout mechanism exits the stall; waiting is unreliable
- Users must forcefully kill the process, losing progress
- A workaround (kill-and-retry) exists but is not reliable for repeated runs

The stall occurs most acutely during:
1. **First-run qmd embed**: llama.cpp compiles from source, taking 5–10+ minutes (checkpoint bdd0e5492e95)
2. **Slow Git operations**: Large repo histories or slow filesystems block `git log` parsing
3. **Concurrent background processes**: Multiple qmd invocations each spawn independent llama.cpp builds if no prebuilt binary exists (checkpoint bdd0e5492e95)

## Partial Progress

Commit ec9047b addressed some ergonomics with "longer timeout, visible progress, GPU hint" (checkpoint c960454549ca), but this only increased timeout windows and improved visibility—not the underlying stall mechanism. The `reflect ingest --verbose` test with v1.0.0's new broader triage, dynamic categories, and auto qmd reindex was never completed due to this stalling (checkpoint 9c595bc9b42d).

## Solution Approaches to Investigate

**Timeout Strategy**: Set explicit timeouts on qmd embed, qmd update, `git log`, and session parsing steps. Exit cleanly with a resumable checkpoint if any operation times out; make timeout configurable via `--timeout` flag.

**Chunking Strategy**: Process evidence in smaller batches (e.g., recent commits first, then older history). Allow incremental progress reporting and resumability across chunks so partial ingests don't lose work.

**Pre-flight Checks**: Detect slow/unavailable tools before entering evidence phase; warm up llama.cpp during `reflect init` or cache prebuilt binaries to avoid repeated from-source compilation (checkpoint bdd0e5492e95).

**Async Background Processing**: Spawn long-running tasks as truly background processes with separate monitoring. Return control to the user immediately while indexing proceeds in background; provide `reflect ingest --status` to check progress.

## Next Steps

- Complete the `reflect ingest --verbose` test on v1.0.0 in a less-constrained environment to confirm the stall (checkpoint 9c595bc9b42d)
- Profile which evidence-gathering step actually stalls longest: qmd embed, git history, or session parsing?
- Implement timeout + chunking pattern (preferred) or async background approach with resumability
