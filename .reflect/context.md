# Dynamic Project Knowledge
<!-- GENERATED OVERLAY — this file is a computed view, not a source of truth -->
<!-- Regenerated from scratch by /reflect from typed records in .reflect/ -->
<!-- Human-authored rules in CLAUDE.md always take precedence over this file -->
<!-- Last updated: 2026-04-03T11:00:00Z -->
<!-- Source: 3 insights, 3 decisions, 0 file maps -->
<!-- Entries expire when their freshness score drops below the configured threshold -->

## Active Rules
<!-- HIGH confidence insights, sorted by freshness descending -->
- Always verify CLI command signatures with --help or docs before documenting (HIGH, 2x) — fresh, confirmed 1 day ago
- Confirm architecture decisions (optional vs required, additive vs replacement) with user before implementing (HIGH, 2x) — fresh, confirmed today
- Keep repo descriptions aligned across all surfaces — check GitHub, README, CLAUDE.md, SKILL.md when changing positioning (HIGH, 3x) — fresh, confirmed today

## Key Decisions
<!-- Accepted decisions, most recent first -->
- **Remove .claude/reflections.md backward compatibility**: Forward-only — legacy format dropped in favor of structured `.reflect/` store. No migration needed given early-stage user base. (2026-04-03)
- **Default session_start to auto**: Zero-friction context freshness — every session auto-analyzes new evidence. Users can opt out via `session_start: manual` in config. (2026-04-03)
- **Agent-agnostic evidence store format**: `.reflect/` uses plain Markdown + YAML frontmatter, readable by any AI coding tool. SPEC.md is the interoperability contract. (2026-04-02)

## Watch Out
<!-- Recent failure patterns and pitfalls, if any -->
- Repo descriptions drift across surfaces (GitHub, README, CLAUDE.md, SKILL.md) — update all when changing project positioning (seen 3x)
