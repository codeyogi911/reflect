# reflect

**Every session teaches the next one.** Cross-session learning for AI coding agents.

Reflect is a persistent, compounding knowledge base for any repository. It reads raw evidence from [Entire CLI](https://entire.dev) sessions and git history, extracts everything worth remembering — decisions, preferences, patterns, gotchas, business rules, architecture, brand — and compiles it into a wiki at `.reflect/wiki/`. The wiki is indexed by [qmd](https://github.com/qubicfox/qmd-cli) for hybrid search (BM25 + vector + reranking). Agents query qmd directly for project memory — no context injection needed.

The more sessions you run, the smarter the next one starts.

## Quick start

```bash
uv tool install reflect-cli
cd your-repo
reflect init
reflect ingest
```

Your next coding session inherits everything reflect has learned.

## What it does

```text
 Session 1 ──┐
 Session 2 ──┤  Evidence pipeline     format.yaml          wiki pages
 Session 3 ──┤  ────────────────────  ─────────────────    ─────────────
 Session N ──┘    Entire CLI            user-defined         qmd-indexed
                  + git history         categories           markdown
                  + reverts             + recency             + frontmatter
```

1. **Evidence**: Entire CLI session checkpoints + git log + revert detection.
2. **Triage** (LLM): plan what knowledge belongs in the wiki.
3. **Write** (LLM): produce one markdown page per durable item.
4. **Index** (qmd): hybrid search across the wiki.

Subsequent sessions query qmd to recall project memory. No re-ingest needed
unless new evidence arrives — the SessionStart hook detects it automatically.

## Why this design

- **Project-scoped** — config + wiki commit to git, travel with the repo, visible to every contributor.
- **Source-agnostic** — wiki pages are plain markdown. Read them, search them, edit them by hand.
- **Bounded budget** — default ingest budget is 10¢ per run; deterministic fallback when no LLM.
- **No context injection** — agents pull on demand via qmd; no startup tax on every prompt.

## Next steps

- [Install](install.md) — `uv`, `uvx`, or `pip`.
- [Commands](commands.md) — full CLI reference.
- [Configuration](configuration.md) — env vars and `.reflect/format.yaml` schema.
- [Skill & Hooks](skill.md) — how reflect integrates with Claude Code.
- [Specification](spec.md) — formal `.reflect/` directory format.
