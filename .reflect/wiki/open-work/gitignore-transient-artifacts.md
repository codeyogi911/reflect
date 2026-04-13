---
created: 2026-04-13
updated: 2026-04-13
sources: [checkpoint 9c595bc9b42d, commit 0839021]
tags: [gitignore, testing, repo-hygiene]
status: active
related: [open-work/test-reflect-init-flow-with-qmd]
---

# Verify .gitignore Excludes All Transient Test Artifacts

## Problem

During `reflect init` and `reflect ingest` testing cycles, transient artifacts (notably `wiki.bak` and similar backup files) were being created but leaving the working tree dirty. This forced context switches to commit housekeeping changes and interrupted the testing workflow by triggering the stop-hook git check. (checkpoint 9c595bc9b42d)

## Action Attempted

In commit 0839021 (2026-04-12), `.gitignore` was updated with the message "chore: sync installed skills, gitignore qmd-managed artifacts". The change added patterns to exclude transient state, likely targeting `wiki.bak` and other ephemeral files produced by `reflect ingest` and qmd embed operations. (checkpoint 9c595bc9b42d)

## What Needs Verification

1. **Completeness**: Verify that all transient test artifacts created by `reflect init` and `reflect ingest` are covered (e.g., `wiki.bak`, qmd temporary files, backup directories)
2. **Pattern correctness**: Confirm patterns are broad enough to catch variants (e.g., `wiki.bak`, `wiki.bak.1`) but narrow enough to avoid accidentally ignoring tracked files
3. **Clean test cycles**: Run a full test sequence (init → ingest → embed) and confirm the working tree remains clean with zero untracked changes
4. **Idempotency**: Verify that repeated test runs don't accumulate dirty state

## Context

This verification became a critical item after discovering that the stop-hook git check was firing mid-test due to uncommitted changes. The `.gitignore` update was part of commit 0839021, but validation was deferred until a less constrained test environment could be arranged. (checkpoint 9c595bc9b42d)
