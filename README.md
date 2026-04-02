# Reflect

**Portable, repo-owned memory for AI coding agents.**

AI agents have memory — but it's machine-local and vendor-specific. Claude's memory lives under `~/.claude/projects/` on your laptop. Cursor's lives somewhere else. Switch machines, switch agents, onboard a teammate — the memory doesn't travel.

`/reflect` solves this by putting memory where it belongs: **in the repo**. Decisions, failure patterns, and working context are stored as structured Markdown in `.reflect/`, versioned with git, reviewable in PRs, and readable by any compliant agent. Entire CLI captures the evidence; `/reflect` interprets it.

**Claude remembers for Claude. `.reflect/` remembers for the project.**

Works with **Claude Code** and **Cursor**. Requires [Entire CLI](https://entire.io) for session capture.

## How It Works

```
Session → Entire CLI captures → /reflect interprets → .reflect/ evidence store → context briefing → next session
```

1. **Entire CLI** captures your coding sessions (Claude Code + Cursor) — this is the evidence substrate
2. `/reflect` interprets transcripts: extracts decisions, patterns, and insights from that evidence
3. Interpretations are stored in `.reflect/` — structured, git-portable, agent-agnostic
4. A **compiled briefing** (`.reflect/context.md`) is generated with the most relevant current context
5. Optionally reference `@.reflect/context.md` from your `CLAUDE.md` as supplementary context

**Important**: `CLAUDE.md` remains the human-owned source of truth for your project rules. `context.md` is a generated briefing that supplements it — it never overrides or replaces human-authored instructions.

## Prerequisites

- **[Entire CLI](https://entire.io)** for session capture
- At least one completed session to analyze

If Entire CLI isn't installed, `/reflect` will detect it and walk you through setup.

## Install

### One-liner

```bash
git clone https://github.com/codeyogi911/reflect.git && \
mkdir -p ~/.claude/skills/reflect && \
ln -sf "$(cd reflect && pwd)/SKILL.md" ~/.claude/skills/reflect/SKILL.md && \
ln -sf "$(cd reflect && pwd)/templates" ~/.claude/skills/reflect/templates
```

### Step by step

```bash
# 1. Clone the repo
git clone https://github.com/codeyogi911/reflect.git

# 2. Create the skill directory
mkdir -p ~/.claude/skills/reflect

# 3. Symlink the skill files (keeps you up to date with git pull)
ln -sf "$(cd reflect && pwd)/SKILL.md" ~/.claude/skills/reflect/SKILL.md
ln -sf "$(cd reflect && pwd)/templates" ~/.claude/skills/reflect/templates
```

### Verify installation

```bash
ls -la ~/.claude/skills/reflect/
# You should see SKILL.md and templates/ pointing to your cloned repo
```

### Compatibility

| Tool                               | Works? | Notes                                  |
|------------------------------------|--------|----------------------------------------|
| **Claude Code** (CLI, Desktop, Web) | Yes    | Skills loaded from `~/.claude/skills/` |
| **Cursor**                          | Yes    | Automatically loads `~/.claude/skills/` |

### Updating

```bash
cd reflect && git pull
```

Because the install uses symlinks, pulling updates takes effect immediately.

### Uninstall

```bash
rm -rf ~/.claude/skills/reflect
```

## Commands

### Analyze sessions (default)

```text
/reflect                          — analyze last 5 sessions
/reflect last 3 sessions          — scope to 3 most recent
/reflect and bake                 — analyze + auto-bake HIGH insights
/reflect [session-id]             — analyze a specific session
/reflect auth issues              — find sessions about auth problems
/reflect slow builds and bake     — topic search + auto-bake
```

### Query the evidence store

```text
/reflect why src/auth/middleware.ts    — decision trail for a file
/reflect context                       — regenerate the context briefing
/reflect what-failed testing           — failure patterns about testing
/reflect status                        — evidence store dashboard
/reflect search database               — search all knowledge artifacts
```

### Topic Search

Any argument that isn't a recognized command, number, session ID, or "and bake" is treated as a topic search. The skill uses semantic matching — `/reflect auth issues` will match sessions about "JWT refresh bugs" or "login redirect loops".

- Searches across **all** sessions, not just recent ones
- Combinable with "and bake"
- Caps at 10 matched sessions per run

## The Evidence Store (`.reflect/`)

After running `/reflect`, your project gets a `.reflect/` directory:

```
.reflect/
├── index.md            # Master lookup table
├── sessions/           # One file per analyzed session (intent, outcome, patterns)
├── decisions/          # Architectural Decision Records — the durable primitives
├── insights/           # Patterns that compound across sessions (with confidence + freshness)
├── files/              # Best-effort file knowledge cache (convenience index, not canonical)
├── context.md          # Compiled briefing — generated, NOT a source of truth
└── history/            # Archived stale data
```

**Decisions and insights are the durable primitives.** Sessions are the evidence. File maps are a convenience cache rebuilt from sessions. `context.md` is a compiled view regenerated on demand — never the canonical source.

Everything is plain Markdown with YAML frontmatter — git-friendly, human-readable, diffable.

See [`SPEC.md`](SPEC.md) for the full, agent-agnostic format specification — useful if you're building a tool that reads from or writes to `.reflect/`.

## Context Briefing

`/reflect` compiles a context briefing from the evidence store — a filtered, prioritized summary of what the AI needs to know for the current state of the project.

### Setup

Optionally add one line to your `CLAUDE.md`:

```markdown
@.reflect/context.md
```

This supplements your `CLAUDE.md` with evidence-backed context:

- **Active Rules** — HIGH-confidence insights from real session evidence, with expiry dates
- **Key Decisions** — architectural choices with reasoning (these don't decay)
- **Watch Out** — failure patterns to avoid

**`CLAUDE.md` is the constitution. `context.md` is the briefing.** If they conflict, CLAUDE.md wins. The briefing never overrides human-authored rules — it only adds evidence-backed supplementary context.

### Freshness Decay

Temporal insights decay over time. Architectural insights decay much more slowly (365-day vs 60-day half-life):

| Days since last seen | Temporal | Architectural |
|---------------------|----------|---------------|
| Today | 1.0 | 1.0 |
| 60 days | 0.50 | 0.89 |
| 120 days | 0.25 | 0.79 |
| 365 days | 0.02 | 0.50 |

Stale insights drop out of the briefing automatically. Recurring patterns stay fresh. Contradicted insights are excluded regardless of freshness.

## How Bake-In Works

When you run `/reflect and bake` (or confirm when prompted), HIGH confidence insights get written as actionable instructions:

- **If you have agent files** (`.claude/agents/*.md`): insights go into the relevant agent's `## Project-Specific Rules` section
- **If you only have CLAUDE.md**: insights go into a `## Session Insights` section
- Insights are never duplicated — the skill checks what's already baked in

## Confidence Levels

| Level | Criteria | What Happens |
|-------|----------|--------------|
| **HIGH** | Seen in 2+ sessions, or 3+ retries, or promoted from MEDIUM | Offered for bake-in, included in context.md |
| **MEDIUM** | Seen once but caused failure or major time sink | Logged, promoted to HIGH on recurrence |
| **LOW** | Minor or uncertain pattern | Logged for reference |

## FAQ

**Q: Does this work without Entire CLI?**
No. Session transcripts are needed for analysis — Entire CLI is what captures them.

**Q: Will it modify my code?**
No. It only writes to `.reflect/`, `.claude/reflections.md`, and optionally to `CLAUDE.md` or agent files. It never touches your source code.

**Q: Can I use this on any project?**
Yes. Install once, use everywhere. The skill is global (`~/.claude/skills/`), but the knowledge store is per-project.

**Q: What about `.reflect/` in git?**
Commit the typed records (`.reflect/sessions/`, `.reflect/decisions/`, `.reflect/insights/`, `.reflect/files/`, `.reflect/index.md`) so team members benefit from shared knowledge. Add `.reflect/context.md` to `.gitignore` — it's a generated overlay that each developer regenerates locally via `/reflect context`. Recommended `.gitignore` entry:
```
.reflect/context.md
```

**Q: What about secrets in session data?**
`/reflect` never includes file contents, environment variable values, or credentials in knowledge artifacts. If sensitive data appears in session transcripts, it is redacted before writing.

**Q: What if I want to edit knowledge artifacts?**
They're plain markdown. Edit them directly — `/reflect` will respect your changes on the next run.

## For Tool Authors

The `.reflect/` evidence store is an open format. If you're building an AI coding tool, editor plugin, or session capture system, see [`SPEC.md`](SPEC.md) for the full specification. A compliant tool can:

- **Read** from `.reflect/` to give agents project context at session start
- **Write** to `.reflect/` to capture decisions, patterns, and insights from sessions
- **Generate** `context.md` as a compiled briefing for any agent

The spec is independent of `/reflect` the skill — it defines the contract for the evidence store itself.

## Contributing

1. Fork the repo
2. Symlink your fork for development (see Install above)
3. Edit `SKILL.md` to change the analysis workflow
4. Edit `templates/` to change output formats
5. Changes take effect immediately when symlinked — no rebuild needed
6. Submit a PR

## License

MIT
