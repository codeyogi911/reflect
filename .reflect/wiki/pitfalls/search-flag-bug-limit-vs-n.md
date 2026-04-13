---
created: 2026-04-13
updated: 2026-04-13
sources: [checkpoint b2a5adf63dd2, commit 9d724e8]
tags: [qmd, cli-flags, search]
status: resolved
---

# search.py Used --limit Instead of -n Flag (FIXED)

## The Bug

`lib/search.py` used `--limit` as the flag to control qmd result count. This was incorrect; qmd's correct flag is `-n`. 

The bug was *latent*: it would only manifest at runtime when search.py actually invoked qmd, not at import time or during static checks. This made it easy to miss during code review or testing.

## Discovery and Fix

During the session retrofitting reflect to use qmd's agentic-specific CLI flags (`--json`, `--files`, `--min-score`, `--full`), the incorrect `--limit` flag was identified in search.py and corrected to `-n` (checkpoint b2a5adf63dd2, commit 9d724e8).

At the same time, the query timeout was increased from 30s to 60s to accommodate first-run llama.cpp compilation delays.

## Why This Matters

Since qmd is now a core component of the keeper agent's evidence ladder—queried before broader session or git history—the result-count flag must be correct for the system to function properly. Without this fix, any call to search.py would fail to limit results correctly, potentially returning unexpectedly large result sets or erroring when qmd encounters the unknown `--limit` flag.

The qmd CLI does not accept `--limit`; only `-n` is supported for controlling result count across qmd's query types (query, search, vsearch, get, multi-get).
