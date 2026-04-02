# Reflect

**A Claude Code skill that turns your session transcripts into permanent improvements.**

Run `/reflect` after a few coding sessions and get structured analysis of what worked, what didn't, and what your agents (or CLAUDE.md) should learn. Powered by [Entire CLI](https://entire.io) session capture.

## What It Does

1. Reads session transcripts captured by Entire CLI
2. Extracts patterns: retry loops, research gaps, what worked well, time sinks, escalation resolutions
3. Assigns confidence levels (HIGH/MEDIUM/LOW) based on recurrence and severity
4. Writes structured reflections to `.claude/reflections.md`
5. Optionally bakes HIGH confidence insights into your CLAUDE.md or agent files

## Requirements

- [Entire CLI](https://entire.io) installed and enabled in your project
- At least one completed session to analyze

## Install

### Symlink (recommended for development)

```bash
git clone https://github.com/codeyogi911/reflect.git
mkdir -p ~/.claude/skills/reflect
ln -sf "$(pwd)/reflect/SKILL.md" ~/.claude/skills/reflect/SKILL.md
ln -sf "$(pwd)/reflect/templates" ~/.claude/skills/reflect/templates
```

### Copy

```bash
git clone https://github.com/codeyogi911/reflect.git
mkdir -p ~/.claude/skills/reflect
cp reflect/SKILL.md ~/.claude/skills/reflect/SKILL.md
cp -r reflect/templates ~/.claude/skills/reflect/templates
```

## Usage

```
/reflect                     — analyze last 5 sessions
/reflect last 3 sessions     — scope to 3 most recent
/reflect and bake            — analyze + auto-bake HIGH insights
/reflect [session-id]        — analyze a specific session
```

## What It Creates

```
your-project/
└── .claude/
    └── reflections.md    — rolling reflection log (newest first)
```

## How Bake-In Works

When you run `/reflect and bake` (or confirm when asked), HIGH confidence insights get written as actionable instructions into your project:

- **If you have agent files** (`.claude/agents/*.md`): insights go into the relevant agent's `## Project-Specific Rules` section
- **If you only have CLAUDE.md**: insights go into a `## Session Insights` section
- Insights are never duplicated — the skill checks what's already baked in

Over time, your agents and project instructions accumulate real, evidence-based improvements from actual session data.

## How Confidence Works

| Level | Criteria | What Happens |
|-------|----------|-------------|
| **HIGH** | Seen in 2+ sessions, or caused significant rework (3+ retries), or confirmed from a prior MEDIUM | Offered for bake-in |
| **MEDIUM** | Seen once but significant (caused failure or major time sink) | Logged in reflections.md, promoted to HIGH if it recurs |
| **LOW** | Minor or uncertain pattern | Logged for reference |

## License

MIT
