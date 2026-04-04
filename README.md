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

<p align="center">
  <img src="https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Fcodeyogi911%2Freflect%2Fmain%2Fdocs%2Fbadges%2Fcheckpoints.json" alt="checkpoints">
  <img src="https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Fcodeyogi911%2Freflect%2Fmain%2Fdocs%2Fbadges%2Fsessions_total.json" alt="sessions (Entire)">
  <img src="https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Fcodeyogi911%2Freflect%2Fmain%2Fdocs%2Fbadges%2Fsessions_window.json" alt="sessions in 7d window">
  <img src="https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Fcodeyogi911%2Freflect%2Fmain%2Fdocs%2Fbadges%2Ftokens.json" alt="tokens 7d">
  <img src="https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Fcodeyogi911%2Freflect%2Fmain%2Fdocs%2Fbadges%2Fcache_hit.json" alt="cache hit">
  <img src="https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Fcodeyogi911%2Freflect%2Fmain%2Fdocs%2Fbadges%2Flearnings.json" alt="learnings">
  <img src="https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Fcodeyogi911%2Freflect%2Fmain%2Fdocs%2Fbadges%2Fpitfalls.json" alt="pitfalls">
  <img src="https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Fcodeyogi911%2Freflect%2Fmain%2Fdocs%2Fbadges%2Fopen_threads.json" alt="open threads">
</p>

<p align="center"><sub>Snapshot metrics from the maintainer&rsquo;s machine: run <code>reflect metrics --export docs/badges --no-json</code> with <a href="https://entire.dev">Entire CLI</a> enabled, then commit <code>docs/badges/*.json</code>. Shields.io reads those files from <code>main</code>; numbers are not computed per visitor.</sub></p>

<p align="center">
  <a href="#the-problem">Problem</a> &middot;
  <a href="#how-it-works">How It Works</a> &middot;
  <a href="#install">Install</a> &middot;
  <a href="#commands">Commands</a> &middot;
  <a href="#format-config">Format Config</a> &middot;
  <a href="SPEC.md">Spec</a>
</p>

---

## The Problem

Every agent session starts from zero.

A coding agent opens a PR to fix a flaky test. It doesn't know that a different agent tried the same fix last week, that the PR was rejected because it broke a downstream contract, and that the team decided to deprecate the test entirely. So it reopens the same PR.

An agent that resolved 50 incidents has seen patterns — which fixes worked, which caused regressions, which services are fragile after deploys. But that knowledge disappears after every run. The next agent starts fresh.

This is the **context lake** problem ([Zohar Einy, 2026](https://thenewstack.io/hidden-agentic-technical-debt/)): agents need two kinds of context that most setups don't provide.

**Runtime context** — live data about services, ownership, recent deployments. Static markdown files go stale the moment they're written.

**History** — what was tried, why it was decided, what went wrong, what the human corrected, what's still unfinished. Without this, agents repeat mistakes that humans (or other agents) have already resolved.

Reflect solves the history half at the repo level — not just decisions, but corrections, abandoned approaches, hot areas, open threads, and the full reasoning trail behind the code.

---

## What Reflect Does (and Doesn't)

**Does:**
- Makes the past queryable — `reflect why` dumps raw evidence from session transcripts and git history so agents (or humans) can find out *why* something is the way it is
- Keeps context fresh — a subagent regenerates from live sources on every session start, not from a static file someone wrote weeks ago
- Travels with the repo — the format config is committed to git, so every clone gets it
- Works with any AI tool — the output is plain Markdown with references that any agent can follow up on

**Doesn't:**
- Replace runtime context from service catalogs, deployment systems, or live infrastructure
- Work across team members or machines (session history comes from [Entire CLI](https://entire.dev) on the local machine)
- Provide agent registry, governance, or orchestration

**Scope:** Individual developers or small teams sharing a repo.

---

## How It Works

```
Evidence Sources              reflect
┌─────────────────────┐      ┌─────────────────────────┐
│  Entire CLI sessions │─────>│                         │
│  (transcripts,       │      │  format.yaml (sections) │
│   decisions, friction)│      │         +               │
│                      │      │  Claude subagent         │
│  Git history         │─────>│  (synthesizes briefing)  │
│  (commits, diffs)    │      │                         │
└──────────────────────┘      └────────────┬────────────┘
                                           │
                                     context.md
                                     (with references)
                                           │
                                     CLAUDE.md
                                (or any instruction file)
```

1. **Evidence already exists** — Entire captures full session transcripts (what the agent did, what the human corrected, what was decided). Git captures commits.
2. **Evidence gathered on demand** — no copying, no intermediate storage. The pipeline reads Entire + git and builds a normalized evidence document.
3. **Subagent synthesizes** — a Claude subagent reads the evidence and `format.yaml` (which declares what sections you want), produces a context briefing with references. Without Claude CLI, a deterministic fallback slots each checkpoint's parsed fields (learnings, friction, open items) directly into the matching sections — no AI, but still structured and referenced.
4. **Every bullet has a reference** — `(checkpoint abc123)`, `(commit def456)` — so the consuming agent can dig deeper with `entire explain --checkpoint` or `git show`.
5. **Active queries bypass the briefing** — `reflect why` dumps raw evidence for the agent to reason over directly.

---

## Install

```bash
git clone https://github.com/codeyogi911/reflect.git
cd reflect && ./install.sh
```

This installs the `reflect` CLI to `~/.local/bin/`.

Then in any git repo:

```bash
reflect init
```

**That's it.** `reflect init` handles everything:
- Installs [Entire CLI](https://entire.dev) if not found
- Enables Entire for the repo
- Creates `.reflect/` with default `format.yaml` and `config.yaml`
- Installs the Claude Code skill (`.claude/skills/reflect/`)
- Wires `@.reflect/context.md` into `CLAUDE.md`

Reflect works best with [Entire CLI](https://entire.dev) for session transcripts — `reflect init` installs it automatically. Without Entire, you get git-only context (commit messages, not decision traces).

Then generate your first briefing:

```bash
reflect context
```

On a fresh repo with no Entire sessions, context will be sparse — just git history. It gets richer as you accumulate sessions. Cost: ~$0.01/run with Claude CLI (Haiku), free with deterministic fallback.

---

## Commands

### Generate context briefing

```bash
reflect context                  # gather evidence, synthesize, write context.md
```

### Query raw evidence

```bash
reflect why src/auth/middleware.ts    # raw session + git evidence about a file
reflect why "database migration"     # raw evidence about a topic
reflect search "JWT bug"             # grep across all sources
```

### Manage

```bash
reflect init                     # one-stop setup (Entire + .reflect/ + skill + wiring)
reflect init --migrate           # migrate from legacy harness to format.yaml
reflect status                   # show available evidence sources
reflect improve                  # analyze context quality, suggest format.yaml changes
reflect metrics                  # print JSON metrics (tokens, sessions, signals)
reflect metrics --export docs/badges --no-json   # refresh README badge endpoints
```

### Claude Code skill

```bash
/reflect                         # regenerate context
/reflect why auth middleware     # evidence + AI narrative
/reflect search JWT              # search all sources
/reflect status                  # evidence overview
/reflect improve                 # analyze quality, propose format changes
```

### Auto-refresh on session start

A SessionStart hook checks if evidence has changed (new commits, new Entire checkpoints, modified config) and automatically regenerates context when a Claude Code session begins. Configure in `.reflect/config.yaml`:

```yaml
session_start: auto     # regenerate automatically (default)
session_start: manual   # show a reminder instead
```

---

## Format Config

Context generation is controlled by `.reflect/format.yaml` — a declarative config that defines what sections appear in the briefing.

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

  - name: Incomplete or Abandoned Work
    purpose: things that were started but not finished, or reverted — context, not instructions
    max_bullets: 5
    recency: 7d

citations: required
max_lines: 150
```

### Customizing for your project

Edit the sections to match what your project needs. Examples:

```yaml
# Backend service
sections:
  - name: API Contracts
    purpose: breaking changes, version mismatches, migration gotchas
    max_bullets: 8
    recency: 30d

  - name: Performance Landmines
    purpose: queries or patterns that caused incidents
    max_bullets: 5
    recency: 14d

  - name: Incomplete or Abandoned Work
    purpose: things that were started but not finished, or reverted — context, not instructions
    max_bullets: 5
    recency: 7d
```

The section names and purposes are instructions to the subagent — it reads them and fills each section from the evidence. No code required.

### How synthesis works

1. **Evidence gathering** (fixed, internal) — reads checkpoints from Entire CLI and commits from git
2. **Subagent synthesis** — passes evidence + format.yaml to Claude CLI (`claude-haiku-4-5` by default, ~$0.01/run)
3. **Validation** — checks citations present, line budget respected, sections populated
4. **Deterministic fallback** — if Claude CLI is unavailable, maps parsed checkpoint fields to sections directly

### Environment overrides

| Variable | Default | Description |
|----------|---------|-------------|
| `REFLECT_MODEL` | `claude-haiku-4-5-20251001` | Model for synthesis |
| `REFLECT_CONTEXT_BUDGET` | `0.05` | Max spend per synthesis run |

---

## Two Read Paths

| Path | Command | How it works |
|------|---------|-------------|
| **Passive** | `reflect context` | Synthesizes briefing via subagent, writes context.md |
| **Active** | `reflect why <topic>` | Fetches raw evidence, dumps to stdout (agent reasons over it) |

The passive path is a pre-computed summary with references — good for orientation. The active path gives the agent raw evidence when it needs the full story.

---

## `.reflect/` Directory

```
.reflect/
├── format.yaml         # section config (committed to git)
├── context.md          # generated briefing (gitignored)
├── config.yaml         # operational settings (committed)
└── .last_run           # freshness state (gitignored)
```

Evidence lives in Entire and git — reflect just reads it.

See [`SPEC.md`](SPEC.md) for the full specification.

---

## FAQ

**Does this work without Entire CLI?**
Partially. Git history is always available, so you get commit messages and file history. But the real value — corrections, reasoning, abandoned approaches, open threads — comes from Entire session transcripts. `reflect init` installs Entire automatically if it's not found.

**Will it modify my code?**
No. It only writes to `.reflect/` and `.claude/skills/reflect/`, and auto-wires `@.reflect/context.md` into `CLAUDE.md` on first run.

**What about `.reflect/` in git?**
Commit: `format.yaml`, `config.yaml`. Gitignore: `context.md`, `.last_run`.

**Does this work across team members?**
Not yet. Session history comes from Entire on the local machine. Team-scale memory is a future goal.

**How is this different from Claude's built-in memory?**
Claude's memory lives in `~/.claude/projects/` on your laptop. It doesn't travel with the repo, isn't visible to other tools, and can't be customized. Reflect's format config is committed to git, produces tool-agnostic Markdown with references, and is customizable per project.

**I used `.reflect/harness` or `.reflect/notes/` in an older version — what now?**
Run `reflect init --migrate` to move from the legacy harness to `format.yaml`. Notes are no longer used — rely on Entire session evidence and `reflect why`.

---

## Contributing

1. Fork the repo
2. Edit `lib/evidence.py` to change evidence gathering
3. Edit `lib/context.py` to change synthesis pipeline or system prompt
4. Edit `lib/` to change CLI commands
5. Changes take effect immediately via symlinks
6. Submit a PR

## License

MIT
