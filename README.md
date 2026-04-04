<p align="center">
  <h1 align="center">reflect</h1>
  <p align="center">
    <strong>git answers "what changed." reflect answers "why."</strong>
  </p>
  <p align="center">
    Repo-owned memory for AI coding agents.
  </p>
</p>

<p align="center">
  <a href="https://github.com/codeyogi911/reflect/actions/workflows/ci.yml"><img src="https://github.com/codeyogi911/reflect/actions/workflows/ci.yml/badge.svg" alt="CI status"></a>
  <img src="https://img.shields.io/badge/python-3.11%2B-informational" alt="Python 3.11+">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License MIT"></a>
</p>

---

## Quick Start

```bash
# Install reflect (from tar)
curl -fsSL https://github.com/codeyogi911/reflect/releases/latest/download/reflect.tar.gz | tar xz
cd reflect-* && ./install.sh

# Set up any repo
cd ~/your-project
reflect init          # installs Entire CLI, creates .reflect/, wires into CLAUDE.md

# Generate your first briefing
reflect context
```

<details><summary>Development install (from git clone)</summary>

```bash
git clone https://github.com/codeyogi911/reflect.git
cd reflect && ./install.sh
```

</details>

That's it. Your next Claude Code session will have project history injected automatically.

---

## Why

Every agent session starts from zero. An agent doesn't know that another agent tried the same fix last week, that it was rejected because it broke a downstream contract, or that the team decided to deprecate the feature entirely.

Reflect gives agents access to **what was tried, why it was decided, what went wrong, and what's still unfinished** — drawn from [Entire CLI](https://entire.dev) session transcripts and git history. The output is plain Markdown with references that any AI tool can read.

---

## How It Works

```
Entire CLI sessions ──┐
  (transcripts,        │     format.yaml
   decisions, friction)├────►  (what sections     ────► context.md
                       │       you want)                (with references)
Git history ───────────┘         +                         │
  (commits, diffs)           Claude subagent               ▼
                             (synthesizes)             CLAUDE.md
```

1. **Evidence already exists** — [Entire](https://entire.dev) captures full session transcripts. Git captures commits. No extra recording needed.
2. **Gathered on demand** — no intermediate storage. The pipeline reads sources and builds evidence at synthesis time.
3. **Subagent synthesizes** — a Claude subagent reads the evidence and your `format.yaml`, produces a briefing with references. Falls back to deterministic rendering without Claude CLI.
4. **Every bullet has a reference** — `(checkpoint abc123)`, `(commit def456)` — so you or your agent can dig deeper with `entire explain --checkpoint` or `git show`.
5. **Auto-refreshes** — a SessionStart hook detects new commits or checkpoints and regenerates context when your next session begins.

---

## Commands

```bash
# Context briefing
reflect context                      # synthesize and write context.md

# Live queries — raw evidence for the agent to reason over
reflect why src/auth/middleware.ts    # why is this file the way it is?
reflect why "database migration"     # what happened with this topic?
reflect search "JWT bug"             # grep across all sources

# Management
reflect init                         # one-stop setup for any repo
reflect status                       # show available evidence sources
reflect improve                      # analyze context quality, suggest format.yaml edits
reflect metrics                      # print JSON metrics (tokens, sessions, signals)
```

### As a Claude Code skill

The skill triggers automatically when you ask "why" questions, or invoke directly:

```
/reflect                         # regenerate context
/reflect why auth middleware     # evidence + AI narrative
/reflect search JWT              # search all sources
/reflect improve                 # analyze quality, propose changes
```

---

## Customizing Context

Context sections are defined in `.reflect/format.yaml`:

```yaml
sections:
  - name: Key Decisions & Rationale
    purpose: why things are the way they are, not what they are
    max_bullets: 8
    recency: 30d

  - name: Gotchas & Friction
    purpose: things that burned time or surprised the agent
    max_bullets: 6
    recency: 14d

  - name: Open Work
    purpose: unfinished items a new session should pick up
    max_bullets: 5
    recency: 7d

citations: required
max_lines: 150
```

The section names and purposes are instructions to the subagent — it reads them and fills each section from the evidence. Edit them to match your project:

```yaml
# Example: backend service
sections:
  - name: API Contracts
    purpose: breaking changes, version mismatches, migration gotchas
    max_bullets: 8
    recency: 30d

  - name: Performance Landmines
    purpose: queries or patterns that caused incidents
    max_bullets: 5
    recency: 14d
```

Use `/reflect improve` to analyze what's working and what's missing in your current config.

---

## What `reflect init` Does

- Installs [Entire CLI](https://entire.dev) if not found
- Enables Entire for the repo
- Creates `.reflect/` with default `format.yaml` and `config.yaml`
- Installs the Claude Code skill to `.claude/skills/reflect/`
- Wires `@.reflect/context.md` into `CLAUDE.md`

### What goes in git

| File | Git | Purpose |
|------|-----|---------|
| `.reflect/format.yaml` | committed | section config — travels with the repo |
| `.reflect/config.yaml` | committed | operational settings |
| `.reflect/context.md` | gitignored | generated briefing — machine-local |
| `.reflect/.last_run` | gitignored | freshness state |

---

## FAQ

**Does this work without Entire CLI?**
Yes, but you only get git history (commit messages, not decision traces). The real value — corrections, reasoning, abandoned approaches — comes from Entire session transcripts. `reflect init` installs Entire automatically.

**Will it modify my code?**
No. It only writes to `.reflect/` and `.claude/skills/reflect/`, and appends one line to `CLAUDE.md`.

**Does this work across team members?**
Not yet. Session history is local. Team-scale memory is a future goal.

**How is this different from Claude's built-in memory?**
Claude's memory lives in `~/.claude/projects/` on your laptop — it doesn't travel with the repo, isn't visible to other tools, and can't be customized per project. Reflect's config is committed to git and produces tool-agnostic Markdown.

**How much does it cost?**
~$0.01 per context generation (Claude Haiku). Free with the deterministic fallback. Override with `REFLECT_MODEL` or `REFLECT_CONTEXT_BUDGET` env vars.

---

## Contributing

1. Fork the repo
2. Edit `lib/` — changes take effect immediately via symlinks
3. Test: `python3 reflect context` or `python3 reflect why <topic>`
4. Submit a PR

## License

MIT
