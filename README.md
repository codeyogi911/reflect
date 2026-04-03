<p align="center">
  <h1 align="center">reflect</h1>
  <p align="center">
    <strong>git answers "what changed." reflect answers "why."</strong>
  </p>
  <p align="center">
    Portable, repo-owned memory for AI coding agents.
  </p>
</p>

<p align="center">
  <a href="#how-it-works">How It Works</a> &middot;
  <a href="#install">Install</a> &middot;
  <a href="#commands">Commands</a> &middot;
  <a href="#the-evidence-store">Evidence Store</a> &middot;
  <a href="SPEC.md">Spec</a> &middot;
  <a href="ROADMAP.md">Roadmap</a>
</p>

---

## The Problem

AI agents have memory — but it's trapped.

Claude's memory lives in `~/.claude/projects/` on your laptop. Cursor's lives somewhere else. Switch machines, switch agents, onboard a teammate — **the memory doesn't travel.**

Decisions get made, approaches get abandoned, lessons get learned. Then the next session starts fresh and makes the same mistakes.

## The Solution

**Put the "why" in the repo.**

```
git log       →  what happened
git blame     →  who changed this line
git bisect    →  which commit broke it

reflect why   →  why is it this way
reflect brief →  what do I need to know for this task
reflect what-failed → what went wrong before
```

Decisions, failure patterns, and working context — stored as structured Markdown in `.reflect/`, versioned with git, reviewable in PRs, readable by any AI agent or human.

**Claude remembers for Claude. Reflect remembers for the project.**

---

## How It Works

```
                    ┌─────────────┐
                    │  Evidence    │
                    │  Sources     │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────┴─────┐ ┌───┴────┐ ┌────┴─────┐
        │  Entire    │ │  Git   │ │  Manual  │
        │  Sessions  │ │ Commits│ │  Entry   │
        └─────┬─────┘ └───┬────┘ └────┬─────┘
              │            │           │
              └────────────┼───────────┘
                           │
                    ┌──────▼──────┐
                    │  reflect    │
                    │  CLI        │
                    │  (analyze)  │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  .reflect/  │
                    │  Evidence   │
                    │  Store      │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ context.md  │
                    │ (briefing)  │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────┴─────┐ ┌───┴────┐ ┌────┴─────┐
        │ CLAUDE.md │ │.cursor │ │ copilot- │
        │           │ │ rules  │ │ instruct │
        └───────────┘ └────────┘ └──────────┘
```

1. **Evidence flows in** — from Entire CLI session transcripts, git commits, or manual entries
2. **Reflect interprets** — extracts decisions, patterns, and insights
3. **`.reflect/` stores it** — structured, git-portable, agent-agnostic Markdown
4. **Context briefing generated** — filtered, prioritized summary of what matters now
5. **Every AI tool gets it** — auto-wired into `CLAUDE.md` today, with Cursor/Copilot/Windsurf wiring planned

---

## Compatibility

| Tool | Status | How |
|------|--------|-----|
| **Claude Code** (CLI, Desktop, Web) | Supported | Skill loaded from `~/.claude/skills/`, context auto-wired into `CLAUDE.md` |
| **Cursor** | Planned | Will auto-wire into `.cursor/rules/` |
| **GitHub Copilot** | Planned | Will auto-wire into `copilot-instructions.md` |
| **Windsurf** | Planned | Will auto-wire into `.windsurfrules` |
| **Any AI tool** | Works | Reads `.reflect/context.md` directly |

---

## Install

```bash
git clone https://github.com/codeyogi911/reflect.git
cd reflect && ./install.sh
```

That's it. Symlinks keep everything up to date — to upgrade, just `git pull`.

### Verify

```bash
ls -la ~/.claude/skills/reflect/
# SKILL.md and templates/ should point to your cloned repo
```

---

## Commands

### Analyze sessions

```bash
/reflect                          # analyze last 5 sessions
/reflect last 3 sessions          # scope to 3 most recent
/reflect and bake                 # analyze + bake HIGH insights (with approval)
/reflect [session-id]             # analyze a specific session
/reflect auth issues              # find sessions about auth problems
```

### Query the evidence store

```bash
/reflect why src/auth/middleware.ts    # decision trail for a file
/reflect brief auth middleware         # task-focused context for current work
/reflect brief src/auth/               # file-focused context overlay
/reflect context                       # regenerate the full context briefing
/reflect what-failed testing           # failure patterns about testing
/reflect status                        # evidence store dashboard
/reflect search database               # search all knowledge artifacts
```

### Topic search

Any unrecognized argument is treated as a topic search. Semantic matching means `/reflect auth issues` finds sessions about "JWT refresh bugs" or "login redirect loops."

---

## The Evidence Store

After running `/reflect`, your project gets a `.reflect/` directory:

```
.reflect/
├── index.md              # master lookup table
├── context.md            # compiled briefing (generated, gitignored)
├── config.yaml           # optional settings
│
├── sessions/             # what happened (evidence)
│   └── 2026-04-03_abc123.md
│
├── decisions/            # what was decided (durable primitives)
│   └── 0001-use-postgres.md
│
├── insights/             # what was learned (patterns that compound)
│   └── verify-cli-flags.md
│
├── files/                # file knowledge cache (convenience index)
│   └── src--auth--middleware.ts.md
│
└── history/              # archived stale artifacts
```

**Decisions and insights are the durable primitives.** Sessions are evidence. File maps are a convenience cache. `context.md` is a compiled view — never the source of truth.

Everything is plain Markdown with YAML frontmatter. Git-friendly. Human-readable. Diffable.

See [`SPEC.md`](SPEC.md) for the full format specification.

---

## Context Briefing

The briefing is a filtered, prioritized summary of what the AI needs to know right now.

```markdown
# Dynamic Project Knowledge

## Active Rules
- Always check CLI --help before assuming flags (HIGH, 3x) — fresh, confirmed 2 days ago
- Run migrations after schema changes (MEDIUM, 2x) — aging, last confirmed 45 days ago

## Key Decisions
- **Use Postgres over Mongo**: ACID compliance required for payment flows (2026-03-15)

## Watch Out
- Docker compose v1 commands fail silently on CI — use v2 syntax (seen 3x)
```

### How it stays fresh

- **Temporal insights** decay with a 60-day half-life — stale knowledge drops out automatically
- **Architectural insights** decay slowly (365-day half-life) — design decisions persist
- **Contradicted insights** are excluded regardless of freshness
- **Human-authored rules always win** — `CLAUDE.md` is the constitution, `context.md` is the briefing

### Staleness tiers

Each entry carries a human-readable action cue:

| Tier | Freshness | Cue |
|------|-----------|-----|
| **fresh** | > 0.7 | "confirmed 2 days ago" |
| **aging** | 0.3 – 0.7 | "last confirmed 45 days ago — verify before relying on this" |
| **fading** | < 0.3 | "last confirmed 89 days ago — verify against current code" |

### Task-focused context

The static briefing covers everything. For focused work, use `/reflect brief`:

```bash
/reflect brief auth middleware     # only auth-related knowledge
/reflect brief src/auth/           # only decisions and insights for those files
```

---

## Trust Model

Not all evidence is equal. Every record carries provenance:

| Source | Trust Level | Can inform context.md? | Can be baked into instructions? |
|--------|------------|------------------------|--------------------------------|
| Entire session analysis | `verified` | Yes | Yes (with human approval) |
| Git commits | `inferred` | Yes | No |
| PR descriptions | `inferred` | Yes | No |
| Manual entry | `verified` | Yes | Yes (with human approval) |

**Evidence store = open to all sources. Instruction files = human-gated, verified-only.**

Bake-in always requires explicit human approval. No auto-promotion, ever.

---

## Session-Start Behavior

A lightweight hook checks for new evidence at the start of each session:

| Mode | Behavior |
|------|----------|
| `auto` (default) | Regenerates `context.md` from existing evidence, nudges if new sessions exist |
| `manual` | Prints a reminder to run `/reflect` |

```yaml
# .reflect/config.yaml
session_start: manual  # opt out of auto mode
```

---

## Confidence Levels

| Level | Criteria | What happens |
|-------|----------|--------------|
| **HIGH** | Seen in 2+ sessions, or 3+ retries | Surfaced for bake-in approval |
| **MEDIUM** | Seen once, caused failure or time sink | Logged, promoted on recurrence |
| **LOW** | Minor or uncertain | Logged for reference |

---

## FAQ

**Does this work without Entire CLI?**
Not yet. Entire CLI is currently required for session capture. Git-commit-based evidence capture is on the [roadmap](ROADMAP.md) and will make Entire optional.

**Will it modify my code?**
No. It only writes to `.reflect/` and to `CLAUDE.md` (auto-wires `@.reflect/context.md` on first run). Bake-in to instruction files requires your explicit approval.

**What about `.reflect/` in git?**
Commit the evidence (sessions, decisions, insights, files, index.md). Gitignore `context.md` — it's regenerated locally.

```gitignore
.reflect/context.md
```

**What about secrets?**
Reflect never includes file contents, env values, or credentials. Sensitive data is redacted with `[REDACTED]`.

**Can I edit knowledge artifacts directly?**
Yes. They're plain Markdown. Reflect respects your changes on the next run.

---

## For Tool Authors

The `.reflect/` evidence store is an open format. See [`SPEC.md`](SPEC.md) for the full specification.

A compliant tool can:
- **Read** from `.reflect/` to give agents project context
- **Write** to `.reflect/` to capture decisions and patterns
- **Generate** `context.md` as a compiled briefing

The spec is independent of the `/reflect` skill — it defines the contract for the evidence store itself.

---

## Contributing

1. Fork the repo
2. Symlink your fork for development (see Install)
3. Edit `SKILL.md` to change the analysis workflow
4. Edit `templates/` to change output formats
5. Changes take effect immediately — no rebuild needed
6. Submit a PR

## License

MIT
