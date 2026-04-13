---
created: 2026-04-13
updated: 2026-04-13
sources: [checkpoint 9c595bc9b42d]
tags: [tail, buffering, progress, debugging]
status: active
---

# Piping Output to tail Masks Live Progress

When piping long-running CLI output through `tail` (e.g., `command | tail -30`), the entire output stream is silently buffered until the command completes. This makes live progress completely invisible and causes the process to appear hung when it is actually still running.

## The Problem

`tail` does not display output as it arrives — it waits for the stream to close before applying the tail operation. This means:
- No progress indicators visible during execution
- Process appears stalled or frozen
- Terminal shows nothing, making diagnosis impossible
- False impression that the process has hung and needs killing

## When This Occurs

This gotcha surfaces with long-running operations like `qmd embed` that legitimately take minutes to complete (especially during first-run llama.cpp compilation from source). Piping such operations through `tail -30` masks all intermediate output, leaving the user blind to what the system is doing. (checkpoint 9c595bc9b42d)

## Solutions

**Option 1: Run the command directly**  
Skip `tail` entirely to see all output and progress in real-time:
```bash
qmd embed  # Full output, progress visible
```

**Option 2: Log to a file and tail the file**  
Run the command in the background and monitor the log with `-f` (follow):
```bash
command > logfile.txt 2>&1 &
tail -f logfile.txt  # -f streams new lines as they appear
```

This allows real-time progress monitoring while preserving the history for post-completion review.

**Option 3: Use tee to split output**  
Capture the full log while displaying filtered output:
```bash
command | tee logfile.txt | grep "progress\|error"  # See filtered progress, save full log
```

When working with files, always prefer `tail -f` over piping to `tail`, as `-f` streams output as it is written rather than buffering until stream closure.
