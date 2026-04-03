---
schema_version: "1.0"
id: "0003"
title: Remove .claude/reflections.md backward compatibility
date: 2026-04-03
status: accepted
sessions: [816ec965]
files: [SKILL.md, CLAUDE.md, evals/evals.json, templates/reflection-format.md]
superseded_by: null
confidence: HIGH
last_validated: 2026-04-03
---

# Decision: Remove .claude/reflections.md backward compatibility

## Context
The `/reflect` skill originally wrote to `.claude/reflections.md` for backward compatibility with the v1 format. With the structured `.reflect/` evidence store now established and the project pivoting to be agent-agnostic, the legacy format added maintenance burden and confused the data model.

## Options Considered
1. **Remove all backward compat** — delete template, clean references (CHOSEN)
2. **Keep writing to both** — maintain dual-write to .claude/reflections.md
3. **Deprecate gradually** — warn for N sessions, then remove

## Decision
Chose immediate removal. The project is early-stage with few users, so there's no migration burden. The structured `.reflect/` store is strictly superior — keeping the legacy format risks confusing new adopters about which format is canonical.

## Consequences
- Cleaner codebase — one format, one truth
- Any users relying on `.claude/reflections.md` from v1 lose auto-updates (acceptable given small user base)
- `templates/reflection-format.md` deleted
