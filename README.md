# Reflect

**Turn your AI coding sessions into permanent improvements.**

`/reflect` analyzes your session transcripts and extracts what worked, what didn't, and what your AI assistant should learn. Insights get baked directly into your project's `CLAUDE.md` or agent files so the same mistakes never happen twice.

Works with **Claude Code** and **Cursor**. Requires [Entire CLI](https://entire.io) for session capture.

## How It Works

1. Your coding sessions are recorded as transcripts
2. You run `/reflect` when you want to learn from recent sessions
3. The skill extracts patterns: retry loops, research gaps, time sinks, what worked well
4. Each pattern gets a confidence level (HIGH/MEDIUM/LOW) based on severity and recurrence
5. HIGH confidence insights can be baked into your `CLAUDE.md` or agent files as actionable rules

Over time, your project accumulates real, evidence-based instructions from actual session data — not guesses.

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

No configuration needed — both tools pick up skills from `~/.claude/skills/` automatically.

### Updating

```bash
cd reflect
git pull
```

Because the install uses symlinks, pulling updates takes effect immediately. No re-install needed.

### Uninstall

```bash
rm -rf ~/.claude/skills/reflect
```

## Usage

```text
/reflect                          — analyze last 5 sessions
/reflect last 3 sessions          — scope to 3 most recent
/reflect and bake                 — analyze + auto-bake HIGH insights
/reflect [session-id]             — analyze a specific session
/reflect auth issues              — find sessions about auth problems
/reflect slow builds and bake     — topic search + auto-bake
/reflect database migration       — find migration-related sessions
```

### Topic Search

Any argument that isn't a number, session ID, or "and bake" is treated as a topic search. The skill retrieves all session intents and uses semantic matching to find relevant ones — so `/reflect auth issues` will match sessions about "JWT refresh bugs" or "login redirect loops", not just sessions with the exact words "auth issues".

- Searches across **all** sessions, not just recent ones
- Combinable with "and bake" (e.g., `/reflect auth issues and bake`)
- Caps at 10 matched sessions per run

### What happens when you run `/reflect`

1. Reads your session transcripts
2. Looks for patterns (retry loops, failures, successes, time sinks)
3. Cross-references against prior reflections to track recurring issues
4. Writes a structured reflection to `.claude/reflections.md`
5. Shows you the key findings and offers to bake HIGH confidence insights

### Example output

After running `/reflect`, you might see:

> **Sessions analyzed:** 3 (abc123, def456, ghi789)
>
> **Issues found:**
>
> - **CLI flag guessing** (HIGH): In 2/3 sessions, assumed `--format json` flag existed without checking `--help` first. Caused 3+ retries each time.
>
> **What worked:**
>
> - **Test-first approach** in session def456 — zero rework on the auth module.
>
> **Recommendation:** Bake "always check `--help` before assuming CLI flags" into CLAUDE.md?

## What It Creates

```text
your-project/
└── .claude/
    └── reflections.md    — rolling reflection log (newest first)
```

Reflections accumulate over time. When the file grows past 50 entries, older ones get summarized into a historical patterns section automatically.

## How Bake-In Works

When you run `/reflect and bake` (or confirm when prompted), HIGH confidence insights get written as actionable instructions:

- **If you have agent files** (`.claude/agents/*.md`): insights go into the relevant agent's `## Project-Specific Rules` section
- **If you only have CLAUDE.md**: insights go into a `## Session Insights` section
- Insights are never duplicated — the skill checks what's already baked in

## Confidence Levels

| Level | Criteria | What Happens |
| --- | --- | --- |
| **HIGH** | Seen in 2+ sessions, or caused significant rework (3+ retries), or promoted from a prior MEDIUM | Offered for bake-in |
| **MEDIUM** | Seen once but significant (caused failure or major time sink) | Logged, promoted to HIGH if it recurs |
| **LOW** | Minor or uncertain pattern | Logged for reference |

## FAQ

**Q: Does this work without Entire CLI?**
No. Session transcripts are needed for analysis — Entire CLI is what captures them.

**Q: Will it modify my code?**
No. It only writes to `.claude/reflections.md` and optionally to `CLAUDE.md` or agent files. It never touches your source code.

**Q: Can I use this on any project?**
Yes. Install once, use everywhere. The skill is global (`~/.claude/skills/`), but reflections and insights are per-project.

**Q: What if I want to edit a baked insight?**
Just edit the `## Session Insights` section in your `CLAUDE.md` or the `## Project-Specific Rules` section in your agent file. They're plain markdown.

## Contributing

1. Fork the repo
2. Symlink your fork for development (see Install above)
3. Edit `SKILL.md` to change the analysis workflow
4. Edit `templates/reflection-format.md` to change the output format
5. Changes take effect immediately when symlinked — no rebuild needed
6. Submit a PR

## License

MIT
