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
  <a href="#the-problem">Problem</a> &middot;
  <a href="#how-it-works">How It Works</a> &middot;
  <a href="#install">Install</a> &middot;
  <a href="#commands">Commands</a> &middot;
  <a href="#the-harness">The Harness</a> &middot;
  <a href="SPEC.md">Spec</a>
</p>

---

## The Problem

Every agent session starts from zero.

A coding agent opens a PR to fix a flaky test. It doesn't know that a different agent tried the same fix last week, that the PR was rejected because it broke a downstream contract, and that the team decided to deprecate the test entirely. So it reopens the same PR.

An agent that resolved 50 incidents has seen patterns — which fixes worked, which caused regressions, which services are fragile after deploys. But that knowledge disappears after every run. The next agent starts fresh.

This is the **context lake** problem ([Zohar Einy, 2026](https://thenewstack.io/hidden-agentic-technical-debt/)): agents need two kinds of context that most setups don't provide.

**Runtime context** — live data about services, ownership, recent deployments. Static markdown files go stale the moment they're written. Ownership transfers, dependencies change, config values update. The agent doesn't know.

**History** — what was tried, why it was decided, what went wrong, what the human corrected, what's still unfinished. Without this, agents repeat mistakes that humans (or other agents) have already resolved. LLM providers are starting to address this with `memory.md` files, but that memory is siloed per tool, per machine, per developer.

Reflect solves this half of the problem at the repo level — not just decisions, but corrections, abandoned approaches, hot areas, open threads, and the full reasoning trail behind the code.

---

## What Reflect Does (and Doesn't)

**Does:**
- Makes the past queryable — `reflect why` dumps raw evidence from session transcripts and git history so agents (or humans) can find out *why* something is the way it is, what was tried before, and what went wrong
- Keeps context fresh — a harness script regenerates from live sources on every session start, not from a static file someone wrote weeks ago
- Travels with the repo — the harness is committed to git, so every clone gets it
- Works with any AI tool — the output is plain Markdown that gets wired into instruction files (currently Claude Code via `CLAUDE.md`)

**Doesn't:**
- Replace runtime context from service catalogs, deployment systems, or live infrastructure
- Work across team members or machines (session history comes from [Entire CLI](https://entire.dev) on the local machine)
- Provide agent registry, governance, or orchestration
- Do much without Entire CLI — git history alone gives you commit messages, not the reasoning behind them

**Scope:** Individual developers or small teams sharing a repo. The organizational-scale problems (agent sprawl, credential governance, cross-team coordination) need a different kind of tool.

---

## How It Works

```
Evidence Sources                     reflect
┌─────────────────────────┐         ┌──────────────────────┐
│  Entire CLI sessions    │────────>│                      │
│  (transcripts, intents, │         │   .reflect/harness   │
│   corrections, decisions)│         │   (replaceable script)│
│                         │         │                      │
│  Git history            │────────>│   Reads on demand.   │
│  (commits, diffs, blame)│         │   No intermediate    │
│                         │         │   storage.           │
│  Manual notes           │────────>│                      │
│  (.reflect/notes/)      │         └──────────┬───────────┘
└─────────────────────────┘                    │
                                         context.md
                                               │
                                         CLAUDE.md
                                    (or any instruction file)
```

1. **Evidence already exists** — Entire captures full session transcripts (what the agent did, what the human corrected, what was decided). Git captures commits.
2. **Harness reads on demand** — no copying, no intermediate storage. The harness is a Python script that fetches evidence and extracts only hard-to-derive signals: non-obvious learnings, landmines, open threads.
3. **Context briefing generated** — a prioritized Markdown summary wired into the agent's instruction file.
4. **Active queries bypass the briefing** — `reflect why` dumps raw evidence for the agent to reason over directly. Raw traces outperform summaries ([Meta-Harness, 2026](https://arxiv.org/abs/2603.28052)).

### What the harness extracts

The default harness reads Entire's AI-generated session summaries and keeps only what's **hard to derive** from code or git alone:

- **Non-obvious learnings** — constraints, gotchas, and patterns you can't see by reading the code (file:line references and code-structure facts are filtered out)
- **Landmines** — friction and pain points from past sessions so you don't hit them again
- **Open threads** — unfinished work across sessions, auto-pruned against newer outcomes

Session history, hot files, and code-structure facts are deliberately excluded — an agent can get those in 1-2 commands (`entire explain --short`, `git log --stat`, read the file). The context budget goes to signals that require crunching multiple session transcripts.

---

## Install

```bash
git clone https://github.com/codeyogi911/reflect.git
cd reflect && ./install.sh
```

This installs the `reflect` CLI to `~/.local/bin/`. The Claude Code skill ships in-repo at `.claude/skills/reflect/` (project-local). Remove `~/.claude/skills/reflect` if you still have a symlink from an older install.

Then in any git repo:
```bash
reflect init      # creates .reflect/ with default harness
reflect context   # generates your first context briefing
```

### Entire CLI (recommended)

Reflect's main value comes from session transcripts captured by [Entire CLI](https://entire.dev). Without it, you get git history only — commit messages, not decision traces.

```bash
# Install Entire CLI separately — see https://entire.dev
entire enable     # start capturing sessions in this repo
```

---

## Commands

### Generate context briefing

```bash
reflect context                  # run harness, write context.md
```

### Query raw evidence

```bash
reflect why src/auth/middleware.ts    # raw session + git evidence about a file
reflect why "database migration"     # raw evidence about a topic
reflect search "JWT bug"             # grep across all sources
```

### Manage

```bash
reflect init                     # set up .reflect/ in current repo
reflect status                   # show available evidence sources
reflect note "why we chose postgres" # add a manual note
```

### Claude Code skill

```bash
/reflect                         # regenerate context
/reflect why auth middleware     # evidence + AI narrative
/reflect search JWT              # search all sources
/reflect status                  # evidence overview
/reflect improve                 # analyze harness quality, propose fixes
```

---

## The Harness

The harness is the core idea — a replaceable script at `.reflect/harness` that reads raw evidence and generates `context.md`.

### Why a script, not a schema

The [Meta-Harness paper](https://arxiv.org/abs/2603.28052) (Stanford/MIT, 2026) showed that the code determining what context an AI sees matters as much as the model itself. Hand-designed memory structures underperform letting agents search raw evidence.

A static schema can't adapt. A script can:
- Be customized per repo (a backend service needs different context than a design system)
- Be A/B tested (run two harnesses against the same evidence, compare results)
- Self-improve (`/reflect improve` analyzes harness output quality and proposes edits)

### Default harness

Reads Entire CLI + git, ranks by recency, extracts signals (corrections, decisions, hot files, open threads), produces a Markdown briefing. Deliberately simple.

### Custom harness

Replace `.reflect/harness` with any script that follows the contract:

```
reads: Entire CLI + git + notes (on demand)
writes: context to stdout
flags: --max-lines, --format
```

What a custom harness could do:
- Use an LLM to summarize sessions before generating context
- Implement semantic search with embeddings
- Fetch from additional sources (PRs, CI logs, Slack)
- Add confidence levels and decay

The harness is committed to git — different repos evolve different harnesses.

---

## Two Read Paths

| Path | Command | How it works |
|------|---------|-------------|
| **Passive** | `reflect context` | Runs harness, writes context.md (pre-session briefing) |
| **Active** | `reflect why <topic>` | Fetches raw evidence, dumps to stdout (agent reasons over it) |

The passive path is a pre-computed summary — good enough for orientation. The active path gives the agent raw evidence when it needs the full story.

---

## `.reflect/` Directory

```
.reflect/
├── harness             # the replaceable context-generation script
├── context.md          # generated briefing (gitignored)
├── config.yaml         # optional settings
├── .last_run           # freshness state (gitignored)
└── notes/              # manual annotations
```

Evidence lives in Entire and git — reflect just reads it. No sessions/, no decisions/, no insights/.

See [`SPEC.md`](SPEC.md) for the full specification.

---

## FAQ

**Does this work without Entire CLI?**
Partially. Git history is always available, so you get commit messages and file history. But the real value — corrections, reasoning, abandoned approaches, open threads — comes from Entire session transcripts.

**Will it modify my code?**
No. It only writes to `.reflect/` and auto-wires `@.reflect/context.md` into `CLAUDE.md` on first run.

**What about `.reflect/` in git?**
Commit: `harness`, `config.yaml`, `notes/`. Gitignore: `context.md`, `.last_run`.

**Does this work across team members?**
Not yet. Session history comes from Entire on the local machine. If two developers both use Entire in the same repo, they each see only their own sessions. Team-scale memory is a future goal, not a current capability.

**How is this different from Claude's built-in memory?**
Claude's memory lives in `~/.claude/projects/` on your laptop. It doesn't travel with the repo, isn't visible to other tools, and can't be customized. Reflect's harness is committed to git, produces tool-agnostic Markdown, and is a replaceable program you can optimize.

---

## Contributing

1. Fork the repo
2. Edit `harness/default.py` to change default context generation
3. Edit `lib/` to change CLI commands
4. Changes take effect immediately via symlinks
5. Submit a PR

## License

MIT
