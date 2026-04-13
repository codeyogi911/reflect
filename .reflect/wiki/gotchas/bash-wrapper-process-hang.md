---
created: 2026-04-12
updated: 2026-04-13
sources: [checkpoint 9c595bc9b42d]
tags: [bash, subprocess, cleanup, timeout]
status: active
---

# bash Wrapper Can Hang After Node Process Exits

When a bash script spawns a child Node process in the background, the parent shell can hang indefinitely even after the Node process exits. The parent shell persists in a wait state, blocking further execution and consuming resources, while the actual work has already completed.

## Discovery

This issue manifested during `reflect ingest` testing (checkpoint 9c595bc9b42d) when a Node CLI process completed its work but the bash wrapper remained hung, blocking subsequent commands and preventing the test from progressing. The process appeared stuck despite all actual work finishing.

## Root Cause

The bash parent process does not automatically clean up when its child exits — it waits indefinitely unless explicitly terminated with a kill signal. This is particularly problematic for background processes that may stall, fail, or complete without reliable signal propagation back to the parent shell.

## How to Detect

A hung bash wrapper typically manifests as:
- Process still appearing active despite CLI output ceasing
- Parent shell unresponsive to new commands
- Inability to gracefully shut down with SIGTERM
- Continued resource consumption despite work completion

## Solution Pattern

Always pair background child process spawns with explicit kill steps. Don't rely on process exit codes or natural termination to guarantee full cleanup:

```bash
# Spawn child
node-cli &
PID=$!

# Wait with optional timeout
wait $PID || true

# Force cleanup
kill $PID 2>/dev/null || true
```

For processes that stall during slow operations (like evidence gathering), kill-and-retry is more reliable than indefinite waiting (checkpoint 9c595bc9b42d: "Background ingest processes can stall indefinitely on evidence-gathering steps when the CLI is slow; kill-and-retry is more reliable than waiting.").

## Related Issue

Piping long-running CLI output through `tail -N` buffers all output until completion, masking progress and making a running process appear hung when it is actually executing (checkpoint 9c595bc9b42d). For visibility into long operations, run commands directly or log to a file.
