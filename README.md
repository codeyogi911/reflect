<p align="center">
  <h1 align="center">reflect</h1>
  <p align="center">
    <strong>Every session teaches the next one.</strong>
  </p>
  <p align="center">
    Cross-session learning for AI coding agents.
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
curl -fsSL https://raw.githubusercontent.com/codeyogi911/reflect/main/install.sh | bash
```

Then in any git repo:

```bash
reflect init       # installs Entire CLI, creates .reflect/, wires into CLAUDE.md
reflect context    # generate your first briefing
```

Your next Claude Code session starts with lessons from every prior session.

---

## Why

Every agent session starts from zero. Session 12 doesn't know that session 8 tried the same fix and had to revert it, that session 10 discovered a workaround for the flaky API, or that session 11 left the migration half-finished.

Reflect reads [Entire CLI](https://entire.dev) session transcripts and git history, then distills cross-session patterns into lessons: **mistakes become rules, friction becomes gotchas, abandoned approaches become warnings, and unfinished work becomes handoffs**. The output is a plain Markdown briefing with references that any AI tool can read.

The more sessions you run, the smarter the next one starts.

---

## How It Works

```
 Session 1 ──┐
 Session 2 ──┤  Evidence pipeline     format.yaml          context.md
 Session 3 ──┼─────────────────────►  (what lessons   ────► "Don't retry the
   ...       │  extracts signals:      to distill)          batch endpoint —
 Session N ──┤  friction, reverts,         +                it times out on
             │  decisions, open work   Claude subagent      payloads > 5MB"
 Git history ┘  hot files, pitfalls    (synthesizes)        (checkpoint af09)
```

Every past session and commit is raw evidence. Reflect extracts the lessons:

1. **Signals, not summaries** — the evidence pipeline cross-references friction, reverts, and learnings across sessions. A revert in session 5 paired with friction in session 3 becomes a pitfall rule. Repeated file churn across sessions surfaces hot areas.
2. **No recording needed** — [Entire](https://entire.dev) already captures session transcripts. Git already captures commits. Reflect reads both on demand — no extra setup, no intermediate storage.
3. **Subagent distills** — a Claude subagent reads the evidence and your `format.yaml`, distills cross-session patterns into a briefing with references. Falls back to deterministic rendering without Claude CLI.
4. **Every lesson is traceable** — `(checkpoint abc123)`, `(commit def456)` — so you or your agent can dig into the original session with `entire explain --checkpoint` or `git show`.
5. **Learns continuously** — a SessionStart hook detects new sessions and commits, then signals the skill to regenerate context before your next session begins. Set `session_start: manual` in `.reflect/config.yaml` to control this.

---

## Commands

```bash
# Version
reflect --version                    # print installed version

# Context briefing
reflect context                      # synthesize and write context.md
reflect context --max-lines 200      # override line budget
reflect context --verbose            # show subagent progress on stderr

# Search across all evidence sources
reflect search auth                  # words are OR'd by default
reflect search --phrase login bug    # exact phrase match
reflect search migration --limit 20  # up to 20 results per source
reflect search auth --json           # machine-readable output

# Session & timeline exploration (requires Entire)
reflect sessions                     # list recent Entire sessions
reflect sessions <session_id>        # inspect one session in detail
reflect sessions --limit 30 --json   # show more, as JSON
reflect timeline                     # date-grouped view (last 7 days)
reflect timeline --days 14 --json    # expand window, JSON output

# Management
reflect init                         # one-stop setup for any repo
reflect init --migrate               # convert legacy harness to format.yaml
reflect upgrade                      # re-install CLI + update templates, skill, agents
reflect status                       # evidence sources, context freshness, token stats
reflect status --json                # machine-readable output
reflect improve                      # analyze context quality, suggest format.yaml edits
reflect metrics                      # print JSON metrics (tokens, sessions, signals)
reflect metrics --export badges/     # write shields.io endpoint files
reflect metrics --export badges/ --no-json       # export only, suppress stdout JSON
reflect metrics --generate-summaries             # let Entire generate missing summaries (slow)
```

### As a Claude Code skill

The skill triggers automatically when you ask "why" questions. It spawns a **Keeper** subagent for deep history investigations. You can also invoke commands directly:

```
/reflect                         # regenerate context
/reflect search JWT              # search all sources
/reflect sessions                # list recent sessions
/reflect timeline                # date-grouped session view
/reflect status                  # check evidence sources
/reflect improve                 # analyze quality, propose changes
/reflect metrics                 # quantitative health check
/reflect init                    # first-time setup
/reflect upgrade                 # update to latest
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

  - name: Critical Pitfalls
    purpose: "agent mistakes, reverted work, and failed approaches — each entry is a DON'T rule backed by evidence of what went wrong"
    max_bullets: 8
    recency: 90d
    entry_fields:
      - mistake         # what the agent did wrong
      - consequence     # what broke or had to be reverted
      - rule            # the "don't do X because Y" directive for future agents

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

Sections can include `entry_fields` for structured entries (e.g., pitfalls with `mistake`, `consequence`, `rule` fields). Use `/reflect improve` to analyze what's working and what's missing in your current config.

---

## What `reflect init` Does

Run it once per repo. It handles:

- Installing [Entire CLI](https://entire.dev) if not found
- Enabling Entire for the repo (`entire enable --agent claude-code`)
- Creating `.reflect/` with default `format.yaml` and `config.yaml`
- Installing the Claude Code skill to `.claude/skills/reflect/`
- Installing the Keeper agent to `.claude/agents/` (and `.cursor/agents/` if `.cursor/` exists)
- Wiring `@.reflect/context.md` into `CLAUDE.md`

### Upgrading

`reflect upgrade` re-runs the installer to update the CLI itself, then refreshes the skill, agents, and `format.yaml` template to the latest version. If your `format.yaml` has local edits, the old version is backed up to `format.yaml.bak` before overwriting.

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
Yes, but you only learn from git history (commit messages, not decision traces). Commands like `sessions` and `timeline` require Entire. The richest lessons — corrections, reasoning, abandoned approaches, friction — come from Entire session transcripts. `reflect init` installs Entire automatically.

**Will it modify my code?**
No. It writes to `.reflect/`, `.claude/skills/reflect/`, `.claude/agents/` (and `.cursor/agents/` if `.cursor/` exists), and adds an `@.reflect/context.md` reference to `CLAUDE.md` (creating the file if it doesn't exist).

**Does this work across team members?**
Not yet. Session history is local. Team-scale learning is a future goal.

**How is this different from Claude's built-in memory?**
Claude's memory lives in `~/.claude/projects/` on your laptop — it doesn't travel with the repo, isn't visible to other tools, and can't be customized per project. Reflect's config is committed to git, its lessons are distilled from real evidence with references, and the output is tool-agnostic Markdown.

**How much does it cost?**
Default max budget is $0.05 per context generation (Claude Haiku), though typical runs cost less. Free with the deterministic fallback when `claude` CLI is not installed. Override with `REFLECT_MODEL` or `REFLECT_CONTEXT_BUDGET` env vars.

---

## Contributing

PRs welcome. For development, symlink `reflect` to the repo script (or run `python3 reflect …` directly) so `lib/` edits take effect without reinstalling the release tarball.

## License

MIT
