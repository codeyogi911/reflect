---
created: 2026-04-13
updated: 2026-04-13
sources: [checkpoint 9c595bc9b42d, checkpoint bdd0e5492e95]
tags: [reflect init, qmd embed, wiki initialization]
status: active
---

# reflect init Skips Embed When Wiki Empty

`reflect init` implements a guard that **skips the seed embed when the wiki is empty** — that is, when there are no pages to index (checkpoint 9c595bc9b42d). This is by design: qmd cannot index what doesn't exist, so the operation is safely omitted.

## The Gotcha

The gotcha surfaces when you **pre-populate the wiki after init completes**. If you:
1. Run `reflect init` on a fresh repo (wiki is empty, embed is skipped)
2. Manually add pages to the wiki or run `reflect ingest` to populate it

...those pages **will not be indexed** until you manually trigger `qmd update && qmd embed`. Queries against the wiki will fail or return stale results, because qmd's BM25 and vector indexes are out of sync.

## The Fix

The root cause was that `reflect init` did not run an initial embed even when the wiki **already contained pages** at startup time. This was fixed in checkpoint bdd0e5492e95 by adding logic to `lib/init.py` to check for existing pages and queue the embed step. The corrected flow now:

- If wiki is empty at init time → skip embed (no work to do)
- If wiki has pages at init time → run `qmd update && qmd embed` to seed the indexes

## Workaround for Pre-Populated Wikis

If you have a wiki with pages and reflect init was never run, or was run when the wiki was empty, manually trigger:
```bash
qmd update reflect-<repo-name>
qmd embed reflect-<repo-name>
```

The pattern is now part of `lib/init.py`'s startup sequence to detect this condition and handle it automatically (checkpoint bdd0e5492e95).
