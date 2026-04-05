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
  Commands: /reflect, /reflect search <query>, /reflect status,
  /reflect sessions [session_id], /reflect timeline, /reflect improve,
  /reflect metrics. Admin: /reflect init, /reflect upgrade.
allowed-tools: Read, Bash, Glob, Grep
hooks:
  SessionStart:
    - hooks:
        - type: command
          command: "${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh"
metadata:
  author: shashwatjain
  version: '0.5.0'
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
4. `sessions [session_id]` → go to **Command: Sessions**
5. `timeline` → go to **Command: Timeline**
6. `improve` → go to **Command: Improve**
7. `metrics` → go to **Command: Metrics**
8. `init` / `upgrade` → go to **Command: Init & Upgrade**
9. Everything else (including no arguments) → go to **Command: Context**

---

## Command: Context (default)

Regenerate the context briefing:

```bash
reflect context                      # regenerate context briefing
reflect context --max-lines 200      # override line budget from format.yaml
reflect context --verbose            # show subagent progress on stderr
```

This gathers evidence from Entire CLI + git, passes it through the subagent
with the format config, validates output (citations, line budget), and writes
`context.md`. Falls back to deterministic rendering if Claude CLI is unavailable.

Report the result to the user: "Context briefing updated."

If the **SessionStart hook** output contains `REFLECT_AUTO_RUN`, run this
command automatically without user prompting. This keeps the briefing fresh.

---

## Command: Search

**Usage**: `/reflect search <query>` or `/reflect search --phrase <multi-word query>`

```bash
reflect search <query>              # words are OR'd by default
reflect search --phrase <query>     # treat full query as one literal phrase
reflect search <query> --limit 20   # show up to 20 results per source
reflect search <query> --json       # machine-readable JSON output
```

Display the results to the user with source labels. Use `--json` when you need
to parse results programmatically or chain into other tools.

---

## Command: Status

**Usage**: `/reflect status`

```bash
reflect status                      # show evidence sources and context freshness
reflect status --json               # machine-readable JSON output
```

Display the output. If no evidence sources are found, suggest next steps.

---

## Command: Sessions

**Usage**: `/reflect sessions [session_id]`

```bash
reflect sessions                    # list recent sessions with IDs (default: 15)
reflect sessions --limit 30         # show more sessions
reflect sessions <session_id>       # inspect one session in detail
reflect sessions --json             # list as JSON (includes full session_id)
reflect sessions <session_id> --json  # session detail as JSON
```

The list view prints a short session ID prefix (e.g. `[b7f5e89a-ba1]`) on each
line. Use that prefix with `reflect sessions <id>` to drill into detail, or
with `entire explain --checkpoint <id>` to reach transcript-level depth.

Use this after `reflect search` or `reflect timeline` when you need to move
from broad evidence into a specific Entire session.

---

## Command: Timeline

**Usage**: `/reflect timeline [--days N]`

```bash
reflect timeline                    # last 7 days (default)
reflect timeline --days 14          # expand window
reflect timeline --json             # machine-readable output
```

The human view prints session IDs (e.g. `[b7f5e89a-ba1]`) and checkpoint IDs
(e.g. `[cp:af09a953]`) so you can chain into `reflect sessions <id>` or
`entire explain --checkpoint <id>` without switching to JSON.

Use this for time-bounded questions such as "what changed this week" or "what
happened before the revert". It groups recent sessions and checkpoints by date
so you can quickly identify the right period before drilling deeper.

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

## Command: Metrics

**Usage**: `/reflect metrics`

```bash
reflect metrics                          # print JSON summary to stdout
reflect metrics --export badges/         # write shields.io endpoint files
reflect metrics --export badges/ --no-json  # export only, no stdout
reflect metrics --generate-summaries     # let Entire generate missing summaries (slow)
```

Outputs quantitative health of the repo's memory: session count, checkpoint
coverage, context freshness, evidence source availability. Use for dashboards
or CI badges.

---

## Command: Init & Upgrade

```bash
reflect init                # scaffold .reflect/ with default format.yaml
reflect init --migrate      # migrate from legacy harness to format.yaml
reflect upgrade             # update format.yaml, skill, and agents to latest
```

`init` is for first-time setup in a new repo. `upgrade` pulls latest templates
and agent definitions from the installed reflect version without overwriting
user customizations in `format.yaml`.

---

## Deep History: Timeline, Sessions, Entire, Git

Use this short evidence ladder when the answer needs more than the current
briefing:

1. Start with `.reflect/context.md` as the briefing. It is the fastest way to
   get the current narrative and references.
2. Run `reflect status` if you are not sure whether Entire-backed evidence is
   available in this repo.
3. Run `reflect search <query>` for breadth across aggregated evidence when
   you are still locating the right topic, checkpoint, or session.
4. Run `reflect timeline` for time-bounded questions, especially when the user
   cares about a recent window or the order of events.
5. Run `reflect sessions` after search or timeline when you need to navigate by
   session, inspect one session, or pick the right ID before going deeper.
6. Run `entire explain --checkpoint <id>` or `entire explain --commit <sha>`
   once you already have an ID and need transcript-level depth.
7. Use `git log` and `git show` as supplements for commit metadata and diffs.
   Git is useful context, but weak on its own for reconstructing agent
   reasoning or backtracking.

This ladder is also the default workflow for the **Keeper** agent.

---

## Digging Deeper

`context.md` is a briefing — a starting point, not the full story. When an entry
is relevant to your current task, spawn the **Keeper** agent to investigate.
Keeper should read this skill first so it inherits the same command semantics,
then follow the evidence ladder above: start from `context.md`, use
`reflect search`, `reflect timeline`, or `reflect sessions` to locate the right
evidence, and only then drill into raw checkpoints with `entire explain` and
cross-check with git as needed. Keeper returns a sourced narrative.

Spawn Keeper when:

- A context.md entry relates to what you're about to change
- You need to trace a decision across multiple sessions
- You want to understand what was tried vs what landed
- An entry about pitfalls or reverted work is a STOP signal — let Keeper
  verify the constraint before you proceed

Do NOT spawn Keeper when:

- The question is about current code state (read the code instead)
- context.md already fully answers the question with enough detail
- The question is forward-looking ("what should we do") not backward-looking
- You just need a quick git log or diff — run it yourself

---

## Rules

- NEVER read `.entire/metadata/` directly — use `reflect` CLI or `entire` CLI
- To customize context, edit `.reflect/format.yaml` — add project-specific sections
- `.reflect/context.md` is generated — never edit it manually
- NEVER include secrets, API keys, or credentials in output
- **Pitfall/mistake entries are blocking**: if context.md lists a past mistake or revert
  for the area you're about to change, read the linked evidence BEFORE writing code
- When `reflect` or `entire` errors, fall back to `git log` / `git show` — never
  block on a missing tool
- `skill/SKILL.md` is the source of truth; `.claude/skills/reflect/SKILL.md` is a
  copy installed by `reflect init`. If they diverge, skill/ wins
- When parsing structured output from subagents, strip markdown code fences before
  decoding JSON — models wrap JSON in `` ```json `` blocks by default
- Error paths must include diagnostic content; never return opaque placeholders
  like `[CLI error: unknown]`
