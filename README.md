# Self-Improving Agents

**A Claude Code skill that gives your project agents that learn from every build cycle.**

Invoke `/self-improving-agents` in any project and get a full agentic harness — an orchestrator that decomposes goals into tasks, a builder that writes code, a verifier that catches bugs before they ship, a tester that validates user flows, a researcher that investigates before building, and a session-analyzer that mines Entire.io transcripts to make agents smarter after every session.

## Why This Exists

Claude Code is powerful, but complex projects need more than a single prompt. You need:

- **Structured loops** — build, verify, test, retry until quality gates pass
- **Separation of concerns** — the code writer shouldn't review its own work
- **Evidence-based learning** — session transcripts drive agent improvement, not self-reporting
- **Human escalation** — agents should ask when stuck, not guess
- **Project-aware agents** — not generic templates, but agents that know *your* codebase

This skill sets up all of that in one command. It studies your project first — directory layout, code patterns, test infrastructure, conventions — then creates agents tailored to your specific codebase. If you already have agents, it fuses them with ours instead of overwriting.

## How It Works

```
ANALYZE → PLAN → [RESEARCH? → BUILD → VERIFY → TEST → REFLECT]* → DONE
                                                       ↓ (3 fails)
                                                    ESCALATE → human
```

1. **Orchestrator** decomposes your goal into ordered tasks
2. Each task cycles through BUILD → VERIFY (two-gate review) → TEST
3. Failed tasks retry up to 3 times, then escalate to you with context and options
4. Entire captures full session transcripts into checkpoint branches
5. After each loop, the EVOLVE phase mines transcripts and bakes improvements into agents
6. Open gaps and task progress persist across sessions

## Install

### Option 1: Symlink (recommended for development)

```bash
git clone https://github.com/shashwatjain/self-improving-agents.git
mkdir -p ~/.claude/skills/self-improving-agents
ln -sf "$(pwd)/self-improving-agents/SKILL.md" ~/.claude/skills/self-improving-agents/SKILL.md
ln -sf "$(pwd)/self-improving-agents/templates" ~/.claude/skills/self-improving-agents/templates
```

### Option 2: Copy

```bash
git clone https://github.com/shashwatjain/self-improving-agents.git
mkdir -p ~/.claude/skills/self-improving-agents
cp self-improving-agents/SKILL.md ~/.claude/skills/self-improving-agents/SKILL.md
cp -r self-improving-agents/templates ~/.claude/skills/self-improving-agents/templates
```

## Usage

Once installed, open any project in Claude Code and run:

```
/self-improving-agents
```

Or with a goal:

```
/self-improving-agents build a REST API for user management
```

After scaffolding, use the harness:

```
Use the orchestrator to build [your goal]
Use the orchestrator to continue
```

Check state between sessions:

```
Read .claude/gaps.md
Read .claude/progress.md
```

## What Gets Created

```
your-project/
└── .claude/
    ├── agents/
    │   ├── orchestrator.md    — Coordinates build loops, dispatches agents
    │   ├── builder.md         — Writes code, runs tests
    │   ├── verifier.md        — Two-gate code review (spec + quality)
    │   ├── e2e-tester.md      — End-to-end testing, failure classification
    │   ├── researcher.md      — Pre-build investigation
    │   └── session-analyzer.md — Mines Entire transcripts for agent improvement
    ├── gaps.md                — Cross-session blocker and decision tracker
    └── progress.md            — Task completion and session log
```

## Agents

| Agent | What It Does |
|---|---|
| **Orchestrator** | Reads learnings and state, decomposes goals into tasks, drives the build loop state machine, escalates when stuck |
| **Builder** | Studies existing patterns before coding, writes tests first when possible, flags new dependencies, stays within scope |
| **Verifier** | Gate 1: spec compliance (missing/extra/wrong). Gate 2: code quality (security, edge cases, tests). Never approves CRITICAL issues |
| **E2E Tester** | Detects existing test infrastructure, writes targeted tests, classifies failures as app bug vs test bug vs environment |
| **Researcher** | Investigates codebases and docs before building. Cites sources. Reduces ambiguity that would waste build cycles |
| **Session Analyzer** | Mines Entire.io session transcripts during EVOLVE phase. Finds retry loops, research gaps, escalation patterns. Produces improvement signals for bake-in |

## Self-Improvement: Entire-Driven Learning

Agents don't self-report what they learned — that's unreliable. Instead, [Entire.io](https://entire.io) captures full session transcripts (prompts, tool use, responses, retries) into checkpoint branches. A **session-analyzer** agent mines these transcripts to find real patterns — retry loops, research gaps, verification ping-pong, escalation resolutions — and produces actionable improvement signals.

### How It Works

After each build loop, the orchestrator runs an **EVOLVE** phase:

1. The session-analyzer uses `entire explain` CLI to access recent session transcripts
2. It identifies patterns: which agents struggled, where retries happened, what the human had to fix
3. Patterns confirmed across 2+ sessions become **bake-in candidates**
4. The orchestrator **rewrites agent core instructions** to incorporate validated patterns
5. The agent now does the right thing automatically — no notes to re-read

For example, if transcripts show the builder repeatedly triggering retry loops when editing auth middleware (because it only ran single-file tests), the EVOLVE phase edits `builder.md`'s Process section to add "run the full auth test suite after any auth change." The pattern disappears because the agent learned.

Each agent file has a `## Project-Specific Rules` section at the bottom — this is where baked-in improvements live as permanent instructions.

You can trigger evolution manually: `"Evolve the agents"` or `"Analyze session history"`.

### Why This Matters

- **Evidence-based** — improvements come from real transcript data, not agent self-assessment
- **Genuine improvement** — the agent's actual behavior changes, not just its reading list
- **Compounding returns** — each session makes the next one faster and more reliable

## Works With Existing Setups

The skill detects what's already in your `.claude/` directory and adapts:

| Scenario | What Happens |
|----------|-------------|
| **Fresh project** | Studies your codebase, creates agents customized to your stack, patterns, and conventions |
| **Our harness already installed** | Upgrades core instructions to latest, preserves all accumulated knowledge and rules |
| **Different agents exist** | Fuses your existing agents with ours — keeps your project knowledge, adds our structured workflow and self-improvement system |
| **External orchestration** | Asks before touching anything |

When fusing, the skill reads both your agent and our template, identifies what each brings (your project knowledge vs our build loop structure), and creates a unified agent that's better than either alone. Custom agents (deployer, domain experts, etc.) are never touched — they get registered with the orchestrator so it can dispatch to them.

## Entire.io Requirement

The harness requires [Entire.io](https://entire.io) for session capture. During scaffolding, the skill configures Entire hooks in `.claude/settings.json` that fire on session lifecycle events (start, end, task checkpoints). These hooks capture full conversation transcripts into checkpoint branches — the raw data that powers agent improvement.

### Setup

The `entire` CLI must be installed before scaffolding. The skill will detect it and configure hooks automatically (with your confirmation). If Entire is not found, the skill will prompt you to install it.

### What Gets Captured

- Full conversation transcripts (prompts, tool use, responses)
- Session lifecycle events (start, end, phase transitions)
- Task-level checkpoints with file change counts
- Token usage and model information

Agents cannot read `.entire/metadata/` during live work (deny permission). Transcript analysis only happens during the EVOLVE phase via the `entire explain` CLI.

## Key Design Decisions

- **Project-aware from day 1** — Agents are customized to your codebase, not generic templates
- **Fusion over replacement** — Existing agents get merged, not overwritten
- **Entire-driven self-improvement** — Session transcripts mined for patterns, validated ones baked into agent instructions
- **Two-gate verification** — Spec compliance before code quality (don't optimize wrong code)
- **Escalation over guessing** — 3 failures → ask the human with context and options
- **Research-first** — Dedicated research step prevents building on assumptions

## Contributing

Contributions welcome! The main files to edit:

- `SKILL.md` — The skill workflow (what happens when you invoke `/self-improving-agents`)
- `templates/*.md` — The agent prompt templates that get scaffolded into projects
- `README.md` — This file

To test changes locally, symlink and invoke in a test project.

## License

MIT
