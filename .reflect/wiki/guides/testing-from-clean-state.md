---
created: 2026-04-13
updated: 2026-04-13
sources: [checkpoint 9c595bc9b42d, checkpoint bdd0e5492e95, checkpoint c960454549ca]
tags: [testing, qmd, cleanup, initialization]
status: active
related: [guides/qmd-integration, guides/reflect-init]
---

# Testing reflect from Scratch

When testing reflect end-to-end from a completely clean state, you must wipe **both** the `.reflect/` directory **and** the qmd collection independently. Failing to do either will leave stale state that blocks subsequent test runs (checkpoint 9c595bc9b42d).

## Three-Step Cleanup Procedure

### 1. Remove `.reflect/` Directory

```bash
rm -rf .reflect/
```

This deletes all wiki pages, commit logs, and ingestion state. `reflect init` will recreate it on the next run.

### 2. Deregister the qmd Collection

After wiping `.reflect/`, you **must** also remove the qmd collection:

```bash
qmd rm reflect-<repo-name>
```

Replace `<repo-name>` with your actual repository name. This step is **critical** — stale qmd collections retain broken path references to the deleted wiki. Attempting to re-ingest without this step will fail because qmd indexes still point to files that no longer exist (checkpoint 9c595bc9b42d).

### 3. Kill Duplicate Background Processes

If previous test runs left `qmd embed` or node processes running, kill them before running `reflect init`:

```bash
pkill -f "qmd embed"
pkill -f "node.*qmd"
ps aux | grep -E "(qmd|node)" | grep -v grep
```

This is essential because concurrent qmd processes each trigger their own llama.cpp build from source, doubling or tripling compile time (5-10 minutes wasted per duplicate). Additionally, a bash wrapper process can remain hung after the underlying node process exits, requiring a separate kill step (checkpoint bdd0e5492e95).

## Running Tests Cleanly

After cleanup, run:

```bash
reflect init
```

This will recreate `.reflect/`, install the qmd skill to `.claude/skills/qmd/`, and register a fresh qmd collection. The init correctly skips the seed embed when the wiki is empty (checkpoint 9c595bc9b42d).

**For observability:** Avoid piping output through `tail` — it silently buffers everything until completion, masking progress and making it appear the process is hung. Run commands directly or redirect to a log file for live output (checkpoint 9c595bc9b42d).

## Known Issues

- **Vulkan prebuilt conflict:** node-llama-cpp auto-selects the Vulkan prebuilt over CPU-only when both are installed, then fails to compile from source if the Vulkan SDK is absent. If you see a Vulkan compile error and only have CPU, explicitly remove the Vulkan package (checkpoint 9c595bc9b42d).
- **Ingest stalling:** If `reflect ingest` stalls on evidence gathering when the CLI is slow, kill and retry rather than waiting indefinitely. Timeout-based retries are more reliable (checkpoint 9c595bc9b42d).
