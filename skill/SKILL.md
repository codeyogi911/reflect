---
name: reflect
description: >
  Answers questions about project history, past decisions, and how things
  evolved. Use this skill whenever the user asks "why" about code, files,
  architecture, or decisions — e.g., "why was this file deleted", "why did
  we switch to X", "what happened with Y", "who changed Z and why". Also
  use for retrospectives, post-mortems, understanding past sessions, learning
  from recent work, onboarding context ("what do I need to know about this
  repo"), and any question that is best answered by consulting git history
  or past AI session transcripts. Even if the user doesn't say "reflect" or
  "history" explicitly, if the answer lives in the past — use this skill.
  Commands: /reflect, /reflect search <query>,
  /reflect status, /reflect improve.
allowed-tools: Read, Bash, Glob, Grep
hooks:
  SessionStart:
    - hooks:
        - type: command
          command: "${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh"
metadata:
  author: shashwatjain
  version: '5.0'
---

# Reflect — Repo-Owned Memory

You help users query and manage repo-owned memory for AI coding agents.
Reflect reads raw evidence from Entire CLI sessions and git history on demand
— no intermediate storage. A declarative `format.yaml` controls what sections
appear in the context briefing; a Claude subagent synthesizes high-quality
briefings with references. Live queries dump raw evidence for you to reason over.

Parse $ARGUMENTS to determine which command to run:

1. `search <query>` → go to **Command: Search**
2. `status` → go to **Command: Status**
3. `context` → go to **Command: Context**
4. `improve` → go to **Command: Improve**
5. Everything else (including no arguments) → go to **Command: Context**

---

## Command: Context (default)

Regenerate the context briefing:

```bash
reflect context
```

This gathers evidence from Entire CLI + git, passes it through the subagent
with the format config, validates output (citations, line budget), and writes
`context.md`. Falls back to deterministic rendering if Claude CLI is unavailable.

Report the result to the user: "Context briefing updated."

If the **SessionStart hook** output contains `REFLECT_AUTO_RUN`, run this
command automatically without user prompting. This keeps the briefing fresh.

---

## Command: Search

**Usage**: `/reflect search <query>`

```bash
reflect search <query>
```

Display the results to the user with source labels.

---

## Command: Status

**Usage**: `/reflect status`

```bash
reflect status
```

Display the output. If no evidence sources are found, suggest next steps.

---

## Command: Improve

**Usage**: `/reflect improve`

Analyzes context quality and proposes format.yaml changes. This is the self-improvement loop.

```bash
reflect improve
```

Read the full output. It contains:
1. **Context Quality Issues** — missing citations, truncation, empty sections
2. **Evidence Gaps** — signals in sessions that didn't make it into context
3. **Current format.yaml** — the section config to edit

Based on the analysis:
1. Propose specific edits to `.reflect/format.yaml` — add/remove/rename sections,
   adjust max_bullets, change recency windows
2. Show the user the diff and explain why each change helps
3. After approval, apply the edits and re-run `reflect context` to verify
4. Run `reflect improve` again to confirm the issues are resolved

**This is the core learning loop**: the format controls what gets synthesized,
the improve command evaluates quality against real evidence, and the user
tunes sections to match what their project actually needs.

---

## Digging Deeper from context.md

The injected `context.md` is a briefing — a starting point, not the full story.
When an entry is relevant to your current task, **go deeper before acting on it**.

Each entry includes a checkpoint reference like `(checkpoint 90e2641946db)`.
Use the `entire` CLI to explore the raw evidence behind any signal:

- **Expand a checkpoint** — get the full session context behind a context.md entry:
  ```bash
  entire explain --checkpoint <id>         # detailed view with prompts + files
  entire explain --checkpoint <id> --full  # full parsed transcript
  ```

- **Browse recent sessions** — find relevant sessions for a topic:
  ```bash
  entire explain                           # list checkpoints on current branch
  entire explain --session <id>            # filter to a specific session
  entire sessions list                     # list all sessions across worktrees
  ```

- **Explain a commit** — understand what happened around a specific change:
  ```bash
  entire explain --commit <sha>
  ```

**When to dig deeper:**
Read `.reflect/format.yaml` to understand which sections exist in context.md.
Any entry that relates to your current task deserves a deeper look — expand
the linked checkpoint or commit to get the full story before acting on it.
Entries about pitfalls, mistakes, or reverted work are STOP signals — read
the evidence before proceeding.

**When the briefing is enough:**
- The entry gives you a clear, actionable fact (e.g., "use os.path.realpath not abspath")
- You're doing unrelated work and the entry is just background context

---

## Agent: reflect-query

A `reflect-query` agent ships with this skill (installed to `.claude/agents/`).
Spawn it for deep investigations that need multiple searches and evidence synthesis.
It runs autonomously — searches context.md, runs `reflect why` and `reflect search`,
digs into raw checkpoints, and returns a sourced narrative.

Use it when a question needs more than a single `/reflect why` call — e.g., tracing
a decision across multiple sessions, comparing what was tried vs what landed, or
building onboarding context for a new contributor.

---

## Rules

- NEVER read `.entire/metadata/` directly — use `reflect` CLI or `entire` CLI
- To customize context, edit `.reflect/format.yaml` — add project-specific sections
- `.reflect/context.md` is generated — never edit it manually
- NEVER include secrets, API keys, or credentials in output
- **Pitfall/mistake entries are blocking**: if context.md lists a past mistake or revert
  for the area you're about to change, read the linked evidence BEFORE writing code
