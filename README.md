# Reflect

**Dynamic repository knowledge for AI coding agents.**

Your repo has amnesia. Git remembers *what* changed — nobody remembers *why*. `/reflect` builds a living knowledge layer from your AI coding sessions: decisions, patterns, insights, and file-level context that grows with every session and makes the next one smarter.

Works with **Claude Code** and **Cursor**. Requires [Entire CLI](https://entire.io) for session capture.

## How It Works

```
Session → Entire CLI captures → /reflect analyzes → .reflect/ knowledge store → context.md → next session
```

1. **Entire CLI** captures your coding sessions (Claude Code + Cursor)
2. `/reflect` analyzes transcripts: extracts patterns, decisions, and insights
3. Knowledge is stored in `.reflect/` — structured, git-friendly, human-readable
4. A **living context file** (`.reflect/context.md`) is auto-generated with prioritized rules, decisions, and file notes
5. Add `@.reflect/context.md` to your `CLAUDE.md` — every session starts with accumulated wisdom

Over time: insights get promoted by recurrence, stale patterns fade via freshness decay, and HIGH-confidence rules get baked into your `CLAUDE.md` or agent files.

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

### Query the knowledge store

```text
/reflect why src/auth/middleware.ts    — decision trail for a file
/reflect what-failed testing           — failure patterns about testing
/reflect search database               — search all knowledge artifacts
/reflect status                        — knowledge store dashboard
/reflect context                       — regenerate the living context file
```

### Topic Search

Any argument that isn't a recognized command, number, session ID, or "and bake" is treated as a topic search. The skill uses semantic matching — `/reflect auth issues` will match sessions about "JWT refresh bugs" or "login redirect loops".

- Searches across **all** sessions, not just recent ones
- Combinable with "and bake"
- Caps at 10 matched sessions per run

## The Knowledge Store (`.reflect/`)

After running `/reflect`, your project gets a `.reflect/` directory:

```
.reflect/
├── index.md            # Master lookup table
├── sessions/           # One file per analyzed session (intent, outcome, patterns)
├── decisions/          # Architectural Decision Records extracted from sessions
├── insights/           # Patterns that compound across sessions (with confidence + freshness)
├── files/              # Per-file knowledge maps (what the AI knows about each file)
├── context.md          # THE dynamic context file (living CLAUDE.md supplement)
└── history/            # Archived stale data
```

Everything is plain Markdown with YAML frontmatter — git-friendly, human-readable, diffable.

## Dynamic Context Injection

The core innovation. Instead of manually maintaining CLAUDE.md rules, `/reflect` generates a living context file that evolves with your project.

### Setup

Add one line to your `CLAUDE.md`:

```markdown
@.reflect/context.md
```

That's it. Every session now starts with auto-generated, prioritized knowledge:

- **Active Rules** — HIGH-confidence insights from real session evidence
- **Key Decisions** — architectural choices with reasoning
- **File Notes** — important facts about recently-touched files
- **Watch Out** — failure patterns to avoid

### Freshness Decay

Insights aren't permanent. They have freshness scores that decay over time:

| Days since last seen | Freshness |
|---------------------|-----------|
| Today | 1.0 |
| 30 days | 0.71 |
| 60 days | 0.50 |
| 120 days | 0.25 |

Stale insights drop out of `context.md` automatically. Recurring patterns stay fresh.

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
We recommend committing `.reflect/` so team members benefit from shared knowledge. Add `.reflect/context.md` to `.gitignore` if you prefer to generate it locally.

**Q: What if I want to edit knowledge artifacts?**
They're plain markdown. Edit them directly — `/reflect` will respect your changes on the next run.

## Contributing

1. Fork the repo
2. Symlink your fork for development (see Install above)
3. Edit `SKILL.md` to change the analysis workflow
4. Edit `templates/` to change output formats
5. Changes take effect immediately when symlinked — no rebuild needed
6. Submit a PR

## License

MIT
