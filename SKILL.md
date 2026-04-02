---
name: reflect
description: >
  Analyze AI coding sessions to build a dynamic knowledge layer for your repo.
  Extracts patterns, decisions, and insights from session transcripts, stores
  them in a structured knowledge base (.reflect/), and generates living context
  that makes every future session smarter. Commands: /reflect (analyze sessions),
  /reflect why <file> (decision trail), /reflect what-failed <topic> (failure
  patterns), /reflect context (regenerate living context), /reflect status
  (knowledge dashboard). Also trigger on "reflect", "session analysis", "what
  went wrong", "what can I improve", "why did we", "what failed".
allowed-tools: Read, Edit, Bash, Glob, Grep
metadata:
  author: shashwatjain
  version: '2.0'
---

# Reflect — Dynamic Repository Knowledge

You analyze session transcripts captured by Entire CLI, extract patterns and
decisions, store them in a structured knowledge base (`.reflect/`), and generate
dynamic context that evolves with every session.

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

### Step 5: Write to Knowledge Store

Read the relevant format templates from the `templates/` directory.

**For each session analyzed:**
1. Read `templates/session-format.md` for the format.
2. Write a session summary to `.reflect/sessions/YYYY-MM-DD_<session-id>.md`.

**For each new or updated insight:**
1. Read `templates/insight-format.md` for the format.
2. Write or update the insight in `.reflect/insights/<slug>.md`.

**For files with meaningful context captured:**
1. Read `templates/file-knowledge-format.md` for the format.
2. Write or update the file knowledge map in `.reflect/files/`.
   - Encode path: replace `/` with `--`, append `.md`.
   - If the file map exists, merge new facts (don't duplicate).

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
   c. Follow the `decisions` references — read each decision record.
   d. Follow the `insights` references — read each insight.

4. If no file knowledge map exists:
   a. Search `.reflect/sessions/*.md` for sessions that mention this file
      in their `files_touched` frontmatter.
   b. Search `.reflect/decisions/*.md` for decisions that reference this file.
   c. Search `.reflect/insights/*.md` for insights from sessions involving
      this file.

5. Compose a **chronological narrative**:
   > "Here's what I know about `<file>`:
   >
   > **What it does**: <from file knowledge map>
   >
   > **Decision trail**:
   > - <date>: <decision or change, with session reference>
   > - <date>: <next event>
   >
   > **Active rules**: <insights that apply to this file>
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

Regenerates `.reflect/context.md` — the dynamic context file that gets injected
into AI sessions via `@.reflect/context.md` in CLAUDE.md.

### Steps:

1. Read the context format template from `templates/context-format.md`.

2. Read `.reflect/config.yaml` if it exists for custom settings. Defaults:
   - `max_lines: 150`
   - `half_life_days: 60`
   - `freshness_threshold: 0.3`

3. **Gather insights**: Read all `.reflect/insights/*.md`. For each:
   - Parse `last_seen` from frontmatter.
   - Calculate freshness: `2^(-(days_since_last_seen / half_life_days))`
   - Filter out insights below freshness threshold.
   - Sort by confidence (HIGH first) then freshness (descending).

4. **Gather decisions**: Read all `.reflect/decisions/*.md`. Filter to
   `status: accepted` from the last 90 days. Sort by date descending.

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
   > "Tip: Add `@.reflect/context.md` to your CLAUDE.md to automatically
   > inject dynamic knowledge into every session."

---

## Command: Status

**Usage**: `/reflect status`

Shows a dashboard of the knowledge store.

### Steps:

1. Count artifacts:
   ```bash
   ls .reflect/sessions/*.md 2>/dev/null | wc -l
   ls .reflect/decisions/*.md 2>/dev/null | wc -l
   ls .reflect/insights/*.md 2>/dev/null | wc -l
   ls .reflect/files/*.md 2>/dev/null | wc -l
   ```

2. Read all insights and calculate freshness for each.

3. Present:
   > **Knowledge Store Status**
   >
   > | Artifact | Count |
   > |----------|-------|
   > | Sessions | N |
   > | Decisions | N |
   > | Insights | N (H HIGH, M MEDIUM, L LOW) |
   > | File Maps | N |
   >
   > **Freshness Distribution**
   > - Fresh (>0.7): N insights
   > - Aging (0.3-0.7): N insights
   > - Stale (<0.3): N insights
   >
   > **Action Items**
   > - N HIGH insights not yet baked
   > - N MEDIUM insights seen 2+ times (promotion candidates)
   > - N stale insights ready for archival
   >
   > **Context file**: `.reflect/context.md` last updated <date>

---

## Command: Search

**Usage**: `/reflect search <query>`

Searches across all knowledge artifacts for a query.

### Steps:

1. Extract the search query from $ARGUMENTS.

2. Search across all `.reflect/` markdown files using Grep.

3. Read matched files and assess relevance semantically.

4. Group results by type (sessions, decisions, insights, file maps).

5. Present the top 10 most relevant results with brief excerpts.

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
