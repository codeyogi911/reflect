---
name: reflect
description: >
  The repo oracle that answers "why," backed by Entire session evidence. Entire
  CLI is the durable write-path and checkpoint substrate; /reflect reads from
  that substrate to extract decisions, failures, and working context. Stores
  interpretations as structured evidence (.reflect/) and compiles context
  briefings for future sessions. Core commands: /reflect (analyze sessions),
  /reflect why <file> (decision trail with receipts), /reflect context
  (compile context briefing). Also: /reflect what-failed <topic>,
  /reflect status, /reflect search. Trigger on "reflect", "session analysis",
  "what went wrong", "what can I improve", "why did we", "what failed".
allowed-tools: Read, Edit, Bash, Glob, Grep
metadata:
  author: shashwatjain
  version: '2.0'
---

# Reflect — Portable Repo Memory

You build portable, repo-owned memory for AI coding agents. Agent memory
(Claude's `~/.claude/projects/`, Cursor's internal state) is machine-local and
vendor-specific. You solve this by putting memory in the repo: decisions,
failure patterns, and working context stored as structured evidence in
`.reflect/`, versioned with git, readable by any agent.

Entire CLI is the durable write-path — it captures and checkpoints sessions.
You read from that evidence substrate to answer "why": why was this decision
made, what failed before, what does the AI need to know right now. You compile
context briefings that supplement (never replace) the project's CLAUDE.md.

Parse $ARGUMENTS to determine which command to run:

1. Strip "and bake" if present → set bake flag (combinable with all commands)
2. Match command:
   - `why <file-or-module>` → go to **Command: Why**
   - `what-failed <topic>` → go to **Command: What-Failed**
   - `context` → go to **Command: Context**
   - `status` → go to **Command: Status**
   - `search <query>` → go to **Command: Search**
   - Everything else → go to **Command: Analyze** (the default)

For the default Analyze command, further parse remaining $ARGUMENTS:
- "last N sessions" or "last N" → limit to N most recent
- A session ID (looks like a hash or short ID) → analyze only that session
- Any remaining text → treat as a **topic search query**
- No scope → default to last 5 sessions
- Cap at 10 sessions per run

---

## Step 0: Prerequisites (all commands)

1. Check if Entire CLI is installed:
   ```bash
   which entire || test -f ~/.local/bin/entire
   ```
   If NOT found → help the user install it:
   - Tell them: "Entire CLI is needed to capture session transcripts. Let me
     help you set it up."
   - Offer to install via Homebrew:
     ```bash
     brew tap entireio/tap && brew install entireio/tap/entire
     ```
     Or if they prefer Go: `go install github.com/entireio/cli/cmd/entire@latest`
   - After installation, ask the user to run `entire login` in their terminal
     to authenticate (this needs interactive input, so the user must run it
     themselves).
   - Once installed, continue.

2. Check if Entire is configured in the current repository:
   ```bash
   entire status
   ```
   If not configured → run `entire enable` to set it up. Report: "Entire is
   now set up! Run some coding sessions, then come back to `/reflect` to
   analyze them." and stop.

   If configured but has no sessions → report "No session history available
   yet. Run some sessions first, then come back to reflect." and stop.

3. Ensure the `.reflect/` knowledge store exists:
   ```bash
   mkdir -p .reflect/sessions .reflect/decisions .reflect/insights .reflect/files .reflect/history
   ```

4. Recommend `.gitignore` for generated artifacts:
   - Check if `.gitignore` exists and whether it already contains `.reflect/context.md`.
   - If not, suggest to the user:
     > "Tip: Add `.reflect/context.md` to your `.gitignore`. It's a generated
     > overlay — the canonical source is the typed records in `.reflect/sessions/`,
     > `.reflect/decisions/`, `.reflect/insights/`, and `.reflect/files/`.
     > Those should be committed; `context.md` should be regenerated locally."

5. **Size budget**: Check the total size of `.reflect/`:
   ```bash
   du -sh .reflect/ 2>/dev/null
   ```
   If the directory exceeds 5MB, warn the user:
   > "Warning: `.reflect/` is over 5MB. Consider running `/reflect status` to
   > identify stale artifacts for archival."
   If `.reflect/index.md` does not exist, create it with:
   ```markdown
   # Reflect Knowledge Index
   <!-- Auto-maintained by /reflect -->
   
   ## Sessions
   | Date | ID | Summary | Outcome |
   |------|-----|---------|---------|
   
   ## Decisions
   | ID | Title | Status | Date |
   |----|-------|--------|------|
   
   ## Insights
   | Slug | Title | Confidence | Times Seen |
   |------|-------|------------|------------|
   ```

---

## Command: Analyze (default)

This is the main command. It analyzes sessions, extracts patterns, and writes
to the knowledge store.

### Step 1: Gather Session Data

1. Run `entire status` for a session overview.

2. Run `entire explain` to get session and commit details.

3. If a **topic query** was detected in $ARGUMENTS:
   a. Run `entire explain --short --search-all` to retrieve all session intents.
   b. Semantically match intents against the topic — be inclusive. "auth issues"
      should match "Fixed JWT refresh bug" or "Debugged login redirect loop".
   c. If no matches → report and stop.
   d. Cap at 10 matches. For each, run `entire explain --session <ID>`.
   e. Note total sessions and match count for the reflection.

### Step 2: Pattern Extraction

Parse session data for these patterns:

**Problems:**
- **Retry loops** — same file edited 3+ times (thrashing)
- **Research-then-fail** — investigation happened but build still failed
- **Verification ping-pong** — rejected, fixed, rejected again
- **Long tool chains** — many sequential Bash/Read/Grep with no Write
- **Token-heavy sessions** — high token count relative to files changed
- **Compaction frequency** — frequent context compression events

**Successes:**
- **Clean first-pass completions** — tasks that succeeded on first try
- **Effective research** — research that prevented failures
- **Fast iterations** — short build-verify cycles that converged quickly

**Opportunities:**
- **Escalation resolutions** — how the human resolved escalations
- **Time sinks** — disproportionate effort relative to complexity
- **Repeated manual steps** — things that could be automated

### Step 3: Decision Extraction

While analyzing sessions, watch for **architectural or design choices** where
alternatives were considered. For each decision found:

1. Read the decision format template from `templates/decision-format.md`.
2. Check `.reflect/decisions/` for existing decisions on the same topic.
   - If a prior decision exists and is confirmed → update `last_validated`.
   - If a prior decision is contradicted → mark it `superseded` and create new.
3. Assign the next sequential ID (read existing files to find the highest).
4. Write the decision record to `.reflect/decisions/<NNNN>-<slug>.md`.

### Step 4: Cross-Reference & Confidence

1. Read existing insights from `.reflect/insights/` — check for recurring
   patterns. If a pattern from a prior session appears again:
   - Update the existing insight: increment `times_seen`, append session ID,
     update `last_seen`, add to Evidence Trail.
   - Promote confidence if warranted (MEDIUM → HIGH on recurrence).

2. Read `CLAUDE.md` if it exists — don't duplicate what's already known.

3. Read `.claude/agents/` if present — check for overlap with existing rules.

4. Also read `.claude/reflections.md` if it exists — check for patterns from
   prior v1 reflections that should be migrated to insights.

5. Assign confidence to each new insight:
   - **HIGH** — seen in 2+ sessions, or 3+ retries, or promoted from MEDIUM
   - **MEDIUM** — seen once but caused failure or major time sink
   - **LOW** — minor or uncertain pattern

6. **Contradiction check**: When creating or updating an insight, search existing
   insights for contradictions. If a new insight directly contradicts an existing
   one (e.g., "always use X" vs "never use X"):
   - Set `contradicted_by: <new-slug>` on the old insight.
   - Set `contradicts: <old-slug>` on the new insight.
   - A contradicted insight is excluded from context.md but NOT deleted.

7. **Negative memory**: If a session shows an approach was tried and deliberately
   abandoned (reverted, caused regressions, or explicitly rejected), create an
   insight with `category: rejected-approach`. These serve as "don't go here
   again" markers and prevent future sessions from re-attempting failed approaches.

8. **Relevance typing**: When creating an insight, assign `relevance_type`:
   - `architectural` if it relates to design patterns, structural choices,
     language constraints, or invariants that won't change with time.
   - `temporal` (default) if it relates to current tooling, dependencies,
     workarounds, or transient conditions.

### Step 5: Write to Knowledge Store

Read the relevant format templates from the `templates/` directory.

**For each session analyzed:**
1. Read `templates/session-format.md` for the format.
2. Write a session summary to `.reflect/sessions/YYYY-MM-DD_<session-id>.md`.

**For each new or updated insight:**
1. Read `templates/insight-format.md` for the format.
2. Write or update the insight in `.reflect/insights/<slug>.md`.

**For files with meaningful context captured** (best-effort cache, not canonical):
1. Read `templates/file-knowledge-format.md` for the format.
2. Write or update the file knowledge map in `.reflect/files/`.
   - Encode path: replace `/` with `--`, append `.md`.
   - If the file map exists, merge new facts (don't duplicate).
   - File maps are a convenience index rebuilt from session data — decisions
     and insights are the durable primitives.

**Update the index:**
- Update `.reflect/index.md` with new sessions, decisions, and insights.

**Backward compatibility:**
- Also write the reflection to `.claude/reflections.md` using the format from
  `templates/reflection-format.md` (insert at top, after header).

### Step 6: Regenerate Context

After every analysis run, automatically regenerate the dynamic context file:
1. Follow the **Command: Context** steps below.
2. This ensures `.reflect/context.md` is always up-to-date.

### Step 7: Display Summary

Show the user:
- Sessions analyzed (count and IDs)
- If topic search: **Topic filter**: {topic} (matched N of total sessions)
- Key patterns found (top 3-5)
- HIGH confidence insights with recommended actions
- New decisions recorded
- Knowledge store stats (total sessions, insights, decisions)

### Step 8: Bake Insights (Optional)

If $ARGUMENTS contains "and bake", or the user confirms when asked:

For each HIGH confidence insight:

1. **Determine the target file:**
   - If the insight maps to a specific agent and `.claude/agents/{agent}.md`
     exists → target that agent file
   - If project-wide or no agents exist → target `CLAUDE.md`
   - Never create new agent files — only append to existing ones

2. **Bake into the target:**
   - For agent files: append to `## Project-Specific Rules` section
   - For CLAUDE.md: append to `## Session Insights` section
   - Write as a clear, actionable instruction
   - Check that a substantially similar insight isn't already baked in

3. **Update the insight file** — set `baked: true` and `baked_to: <target>`

If $ARGUMENTS does NOT contain "and bake":
- Show HIGH confidence insights and ask: "Would you like to bake these
  insights into your project files?"

---

## Command: Why

**Usage**: `/reflect why <file-or-module>`

Shows the full decision trail for a file — every session that touched it,
every decision that shaped it, and every insight related to it.

### Steps:

1. Normalize the file path from $ARGUMENTS (e.g., `src/auth/middleware.ts`).

2. Encode the path (`/` → `--`) and check for `.reflect/files/<encoded>.md`.

3. If the file knowledge map exists:
   a. Read it.
   b. Follow the `sessions` references — read each session summary.
   c. From each session summary, extract `commits` from frontmatter for SHA references.
   d. Follow the `decisions` references — read each decision record.
   e. Follow the `insights` references — read each insight.

4. If no file knowledge map exists:
   a. Search `.reflect/sessions/*.md` for sessions that mention this file
      in their `files_touched` frontmatter.
   b. Search `.reflect/decisions/*.md` for decisions that reference this file.
   c. Search `.reflect/insights/*.md` for insights from sessions involving
      this file.

5. Compose a **structured decision graph with receipts**:
   > "Here's what I know about `<file>`:
   >
   > **What it does**: <from file knowledge map>
   >
   > **Decision trail** (with receipts):
   > - <YYYY-MM-DD> `<commit-SHA-short>` (session `<session-id>`):
   >   <What was decided or changed, and why>
   >   Decision ref: <decision-id if applicable>
   > - <YYYY-MM-DD> `<commit-SHA-short>` (session `<session-id>`):
   >   <Next event>
   >
   > **Competing hypotheses** (where close alternatives existed):
   > - <Decision title>: Chose <option A> over <option B> because <reason>.
   >   Confidence: <HIGH|MEDIUM>. <option B> would be better if <condition>.
   >
   > **Active rules**: <insights that apply to this file, with session citations>
   >
   > **Rejected approaches**: <any `rejected-approach` insights for this file>
   >
   > **Unresolved ambiguity**:
   > - <Things we're not sure about — conflicting evidence, untested assumptions>
   >
   > **Pitfalls**: <common issues from file knowledge map>"

6. If nothing is found → report: "No knowledge found for `<file>`. Run
   `/reflect` to analyze sessions that touched this file."

---

## Command: What-Failed

**Usage**: `/reflect what-failed <topic>`

Shows failure patterns related to a topic, with evidence and recurrence data.

### Steps:

1. Extract the topic from $ARGUMENTS.

2. Search across the knowledge store:
   a. Grep `.reflect/insights/*.md` for the topic and for `category: anti-pattern`
      or `category: pitfall` entries.
   b. Grep `.reflect/sessions/*.md` for sessions mentioning failures related
      to the topic.

3. For each match, read the full file and assess relevance semantically —
   don't rely on exact keyword matches alone.

4. Sort results by: severity (HIGH first), then recency (newest first).

5. Present:
   > "**Failure patterns for '<topic>':**
   >
   > 1. **<pattern>** (HIGH, seen <N>x, last: <date>)
   >    <description with evidence>
   >    Status: <BAKED | NOT BAKED>
   >
   > 2. **<pattern>** (MEDIUM, seen <N>x, last: <date>)
   >    <description>
   >
   > **Sessions with '<topic>' failures:** <list of session IDs with dates>"

6. Suggest baking any unbaked HIGH insights.

---

## Command: Context

**Usage**: `/reflect context`

Regenerates `.reflect/context.md` — a compiled briefing of the most relevant
current context from the evidence store, optionally referenced from CLAUDE.md
via `@.reflect/context.md`. This is a generated overlay, not a source of truth.

### Steps:

1. Read the context format template from `templates/context-format.md`.

2. Read `.reflect/config.yaml` if it exists for custom settings. Defaults:
   - `max_lines: 150`
   - `half_life_days: 60`
   - `freshness_threshold: 0.3`

3. **Gather insights**: Read all `.reflect/insights/*.md`. For each:
   - Parse `last_seen` from frontmatter.
   - Calculate freshness: `2^(-(days_since_last_seen / half_life_days))`.
     Use half_life_days = 365 for `relevance_type: architectural` insights,
     default (60) for `temporal`.
   - Exclude insights where `contradicted_by` is set (they've been superseded).
   - Filter out insights below freshness threshold.
   - Calculate expiry date: the future date when freshness will drop below the
     threshold, given the half-life formula. Include this in context.md output.
   - Cross-check each insight against CLAUDE.md rules. If an insight contradicts
     or conflicts with a human-authored rule in CLAUDE.md, exclude it from
     context.md and log a warning in the summary output.
   - Sort by confidence (HIGH first) then freshness (descending).

4. **Gather decisions**: Read all `.reflect/decisions/*.md`. Filter to
   `status: accepted`. Decisions do not decay — include all accepted decisions,
   sorted by date descending. Cap at 10 for the context file.

5. **Gather file knowledge**: Read all `.reflect/files/*.md`. Filter to files
   whose `last_updated` is within the last 5 sessions (check by date).

6. **Gather failure patterns**: From insights, filter `category: anti-pattern`
   or `category: pitfall` that are NOT baked.

7. **Generate context.md** following the template format:
   - Active Rules: max 15 entries
   - Key Decisions: max 10 entries
   - File Notes: max 10 entries
   - Watch Out: max 5 entries
   - Omit empty sections.
   - Total must stay under the line budget.

8. Write to `.reflect/context.md`.

9. If `@.reflect/context.md` is NOT already in `CLAUDE.md`, tell the user:
   > "Tip: You can add `@.reflect/context.md` to your CLAUDE.md to include
   > this briefing as supplementary context. Your CLAUDE.md rules always
   > take precedence — context.md only adds evidence-backed context."

---

## Command: Status (lightweight)

**Usage**: `/reflect status`

Quick summary of the evidence store. Keep this simple — just counts and
actionable items, not a full dashboard.

### Steps:

1. Count artifacts:
   ```bash
   ls .reflect/sessions/*.md 2>/dev/null | wc -l
   ls .reflect/decisions/*.md 2>/dev/null | wc -l
   ls .reflect/insights/*.md 2>/dev/null | wc -l
   ```

2. Present:
   > **Evidence Store**: N sessions, N decisions, N insights
   > **Unbaked HIGH insights**: N
   > **Context briefing**: last updated <date or "not yet generated">

---

## Command: Search (lightweight)

**Usage**: `/reflect search <query>`

Simple grep across the evidence store — not a semantic search engine.

### Steps:

1. Extract the search query from $ARGUMENTS.

2. Grep across `.reflect/sessions/`, `.reflect/decisions/`, and `.reflect/insights/`
   for the query.

3. Read matched files and present the top 10 most relevant results with type
   labels and brief excerpts.

---

## Rules

- NEVER read `.entire/metadata/` directly — always use Entire CLI commands
- Cite session IDs for every pattern so findings are traceable
- Focus on actionable insights, not statistics for statistics' sake
- If no meaningful patterns emerge, say so — don't fabricate insights
- Don't duplicate insights already in CLAUDE.md or agent Project-Specific Rules
- Keep reflections.md entries concise — quality over quantity
- When updating existing knowledge artifacts, preserve existing content and merge
- Always regenerate context.md after an analysis run
- Template files are in the same directory as this SKILL.md — read them at runtime
- `.reflect/context.md` is a generated overlay — canonical data lives in the typed
  records (sessions/, decisions/, insights/, files/). context.md should be in .gitignore.
- NEVER include file contents, environment variable values, API keys, tokens, passwords,
  or any credential-like strings in knowledge artifacts. If session data contains
  secrets, redact them before writing. Use `[REDACTED]` as a placeholder.
- Total `.reflect/` directory should stay under 5MB. Warn the user and suggest
  archiving stale artifacts to `.reflect/history/` if it grows beyond that.
