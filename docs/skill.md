# Skill & Hooks

`reflect init` installs a Claude Code skill at `.claude/skills/reflect/` and
hooks at `.claude/skills/reflect/hooks/`. This is how agents discover reflect
without anyone editing `CLAUDE.md` by hand.

## The skill (`SKILL.md`)

A single skill file with internal `$ARGUMENTS` dispatch — `/reflect`,
`/reflect ingest`, `/reflect search <query>`, etc. The skill carries:

- **Top-level scope**: explicit "When to use" / "When NOT to use" sections so
  Claude Code can decide whether to invoke the skill at all.
- **Per-command sections** with their own scope and "Common failures"
  troubleshooting.
- **qmd query patterns**: when to use `qmd query` vs `qmd search` vs `qmd vsearch`,
  which agentic flags (`--json`, `--files`, `--min-score`, `--all`) are worth
  reaching for.

The source of truth lives at `src/reflect/_data/skill/SKILL.md` in the
[reflect repository](https://github.com/codeyogi911/reflect). `reflect init`
copies it into your repo's `.claude/skills/reflect/`.

## The Keeper agent

For deeper investigations than the wiki provides, the skill spawns the
**Keeper** subagent (installed at `.claude/agents/keeper.md`). Keeper follows
an evidence ladder: qmd → reflect search/timeline/sessions → raw Entire
checkpoints → git log/show.

Spawn Keeper when:

- Tracing a decision across multiple sessions.
- Verifying a pitfall entry before acting on it.
- Distinguishing "what was tried" from "what landed".

## SessionStart hook

`hooks/session-start.sh` runs at the start of every Claude Code session. It
checks whether the wiki is stale relative to the current git HEAD and Entire
checkpoints, and prints `REFLECT_WIKI_INGEST` when an ingest is warranted.

The agent picks up that signal from the skill and runs `reflect ingest`. With
`session_start: manual` in `.reflect/config.yaml`, the hook only prints a hint
instead of triggering ingest.

The hook is **non-blocking** (always exits 0) so a stale knowledge base never
prevents a session from starting.
