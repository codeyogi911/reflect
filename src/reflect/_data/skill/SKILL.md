---
name: reflect
description: >
  Project knowledge base — accumulated memory from all coding sessions.
  Reflect maintains a wiki that compounds knowledge over time: decisions,
  preferences, patterns, gotchas, architecture, business rules, and anything
  discussed in sessions. Knowledge is searchable via qmd.
  Use this skill when the user asks about past decisions, project history,
  conventions, preferences, or any "why" question. Also use for retrospectives,
  onboarding context, and managing the knowledge base.
  Commands: /reflect, /reflect ingest, /reflect lint, /reflect status,
  /reflect sessions [session_id], /reflect timeline, /reflect search <query>,
  /reflect improve, /reflect metrics.
  Admin: /reflect init, /reflect upgrade.
allowed-tools: Read, Bash, Glob, Grep
hooks:
  SessionStart:
    - hooks:
        - type: command
          command: "${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh"
metadata:
  author: shashwatjain
  version: '1.0.0'
---

# Reflect — Project Knowledge Base

Reflect is a persistent, compounding knowledge base for your project. It reads
session transcripts (Entire CLI) and git history, extracts ALL knowledge worth
remembering, and maintains a wiki at `.reflect/wiki/`. The wiki is indexed by
qmd for hybrid search (BM25 + vector + reranking).

**You don't need to inject context.** The knowledge base is always available
via qmd. When you need project context — past decisions, preferences, patterns,
gotchas — search qmd directly.

## When to use this skill

- The user asks "why" about a past decision, convention, or piece of code.
- You're about to make an architectural choice and want prior context.
- The user mentions onboarding, retrospectives, or "what did we try before".
- You hit unfamiliar code, infra, or tooling and want recorded context.
- The user explicitly invokes `/reflect <subcommand>`.
- The SessionStart hook output contains `REFLECT_WIKI_INGEST` (run `reflect ingest`).

## When NOT to use this skill

- Real-time code navigation — use Grep/Read directly.
- Questions answerable from the live codebase alone (file structure, current implementation).
- Anything where the user has already provided sufficient context.
- Trivial typos, single-file edits, formatting changes.
- When `.reflect/` does not exist in the repo (suggest `reflect init` instead).

Parse $ARGUMENTS to determine which command to run:

1. `ingest` → go to **Command: Ingest**
2. `lint` → go to **Command: Lint**
3. `status` → go to **Command: Status**
4. `search <query>` → go to **Command: Search**
5. `sessions [session_id]` → go to **Command: Sessions**
6. `timeline` → go to **Command: Timeline**
7. `improve` → go to **Command: Improve**
8. `metrics` → go to **Command: Metrics**
9. `init` / `upgrade` → go to **Command: Init & Upgrade**
10. Everything else (including no arguments) → go to **Command: Default**

---

## Accessing Project Memory

The knowledge base is a qmd collection named `reflect-<directory-name>`
(e.g., `reflect-myapp`). When you need to recall project knowledge during any
task, query it directly — qmd provides structured output built for agents.

**Use these patterns — always prefer `--json` or `--files` over plain output:**

```bash
# Get ranked hits with snippets + scores (best for reasoning over results)
qmd query "why do we use Supabase" -c reflect-myapp --json

# Get just the file paths above a relevance threshold, then read them yourself
qmd query "deployment process" -c reflect-myapp --files --min-score 0.4

# Get all matches (not top-10) above a threshold
qmd query "brand colors" -c reflect-myapp --all --min-score 0.5 --json

# Retrieve full document content when you need the complete page
qmd get decisions/database-choice.md --full -c reflect-myapp

# Grab a line range from a large page
qmd get guides/deployment.md:20 -l 40 -c reflect-myapp

# Batch fetch related pages via glob
qmd multi-get "decisions/*.md" -c reflect-myapp --json

# Pure keyword search (BM25, no LLM — fastest)
qmd search "stripe webhook" -c reflect-myapp --json

# Pure semantic search (vector similarity)
qmd vsearch "how do we handle payment retries" -c reflect-myapp --json
```

**Query type cheat sheet:**
- `qmd query` — hybrid (BM25 + vector + LLM reranking) — best quality, use by default
- `qmd search` — BM25 only — fastest, best for exact keywords/names/code
- `qmd vsearch` — vector only — best for semantic questions
- `qmd get` — retrieve a specific page by path
- `qmd multi-get` — batch fetch via glob pattern

**Key agentic flags:**
- `--json` — structured output (prefer this over plain text)
- `--files` — paths only, one per line (for `xargs`, `cat`, agent self-read)
- `--min-score <N>` — threshold filter (0.4-0.6 is a reasonable floor)
- `--all` — return all matches above threshold, not just top-N
- `--full` — full document content (for `qmd get`)
- `-n <N>` — limit results (default 10)
- `--no-rerank` — skip LLM reranking (faster on CPU)
- `-c <collection>` — scope to a specific collection

Use project memory whenever:
- You're about to make an architectural decision (check if there's prior context)
- You need project conventions, preferences, or brand guidelines
- You encounter something unfamiliar in the codebase
- The user asks "why" about anything
- You want to avoid repeating past mistakes

**A dedicated `qmd` skill is also installed** (`.claude/skills/qmd/`) with
detailed guidance on lex/vec/hyde query types, intent steering, and combining
search types. Consult it for advanced queries.

**qmd also ships an MCP server** (`qmd mcp`) that exposes `query`, `get`, and
`status` tools via stdio. If you prefer MCP tool calls over shelling out to
Bash, register qmd as an MCP server in your agent config.

---

## Command: Default

When invoked with no arguments or just `/reflect`:

1. Check if `.reflect/` exists. If not, suggest `reflect init`.
2. Run `reflect status` to show the current state.
3. If evidence has changed since last ingest, suggest `reflect ingest`.

---

## Command: Ingest

**Usage**: `/reflect ingest`

```bash
reflect ingest                      # process new sessions/commits into wiki
reflect ingest --dry-run            # show planned writes without touching disk
reflect ingest --verbose            # show triage + write subagent progress
reflect ingest --force              # suppress non-default-branch warning
```

Ingests new evidence into the wiki via a two-step subagent pipeline:
1. **Triage**: Given new evidence + existing page index, produces a JSON plan.
   Extracts ALL knowledge: decisions, preferences, patterns, gotchas, pitfalls,
   architecture, business rules, brand guidelines — anything worth remembering.
   Can create new wiki categories dynamically.
2. **Write**: For each planned action, produces page content with frontmatter.
3. **Index**: Updates index.md and re-indexes the qmd collection.

Report the result: how many pages were created, updated, or resolved.

### When to use

- The SessionStart hook printed `REFLECT_WIKI_INGEST`.
- After merging a feature branch into the default branch.
- Periodically (e.g., end of week) to keep the wiki current.

### When NOT to use

- Mid-feature on a feature branch (use `--force` only if you want a branch-local wiki).
- When `.reflect/` does not exist (`reflect init` first).
- When the user is asking a question — search the wiki instead.

### Common failures

- **"Not on default branch"**: by design. Merge to `main` first, or pass `--force`.
- **Triage subagent timeout**: re-run; partial progress is preserved via `.last_run`.
- **qmd re-index fails**: check `qmd status -c reflect-<repo>`; the wiki write
  still succeeded, only the search index is stale.

### Branch Policy (Important)

The wiki is **project memory** — it belongs on the default branch (`main`),
not on feature branches. Recommended workflow:

```
1. Develop on feature branches → sessions accumulate in Entire CLI
2. Merge feature branch into main
3. On main: reflect ingest    ← updates canonical wiki
```

`reflect ingest` warns when run on a non-default branch because branch-local
wiki updates create silos and merge conflicts. Entire CLI captures sessions
globally, so ingesting on main still picks up conversations that happened
on any branch. Use `--force` only when you intentionally want a branch-local
wiki (e.g., for experimentation).

---

## Command: Lint

**Usage**: `/reflect lint`

```bash
reflect lint                        # report wiki health issues
reflect lint --fix                  # auto-fix resolvable issues
reflect lint --json                 # machine-readable output
```

Checks wiki health:
- **Stale pages**: updated date older than category recency window
- **Orphan pages**: no inbound related links from other pages
- **Possibly resolved**: open-work pages whose keywords appear in recent git log
- **Coverage gaps**: format.yaml sections with few or no wiki pages
- **Near-duplicates**: pages in the same category with >70% title overlap

`--fix` auto-resolves open-work and archives superseded pages. Returns non-zero
exit code when issues are found.

### When to use

- Periodic wiki audits (weekly/monthly).
- Before a major refactor — see what knowledge might be obsolete.
- After running `reflect ingest` to validate the new pages.

### When NOT to use

- Before `reflect init` (no wiki to lint).
- As part of CI on every commit — runs once per push is enough.

### Common failures

- **Non-zero exit when issues exist**: this is intentional. Use `--fix` or
  `--json | jq '.issues'` to triage; pipe through `|| true` if calling from
  scripts that shouldn't fail.

---

## Command: Search

**Usage**: `/reflect search <query>`

```bash
reflect search <query>              # search across all evidence sources
reflect search --phrase <query>     # exact phrase match
reflect search <query> --wiki-only  # search only wiki pages
reflect search <query> --json       # machine-readable JSON output
```

For richer semantic search, use qmd directly:
```bash
qmd query "<natural language question>" -c reflect-<repo-name>
```

### When to use

- Quick keyword grep across wiki + Entire transcripts + git log in one shot.
- When you don't know which evidence source has the answer.

### When NOT to use

- For natural-language "why" questions — use `qmd query` (semantic).
- For path-only output to feed another tool — use `qmd query --files`.

### Common failures

- **No results across any source**: the term may live in commit bodies — try
  `git log --all --grep "<term>"` directly.

---

## Command: Status

**Usage**: `/reflect status`

Shows evidence source availability, wiki page count, qmd collection status,
and freshness state.

### When to use

- First action when entering a new repo with reflect installed.
- When the SessionStart hook printed nothing and you want to confirm freshness.
- Before suggesting `reflect ingest` to verify there's actually new evidence.

### When NOT to use

- As a substitute for `reflect search` — status doesn't surface content.

---

## Command: Sessions

**Usage**: `/reflect sessions [session_id]`

```bash
reflect sessions                    # list recent sessions
reflect sessions --limit 30         # show more
reflect sessions <session_id>       # inspect one session
```

### When to use

- "What did session N discuss?" / drilling into a specific past conversation.
- Cross-referencing a checkpoint hash to its session of origin.

### When NOT to use

- Searching by keyword — use `reflect search` or `qmd query`.

---

## Command: Timeline

**Usage**: `/reflect timeline [--days N]`

```bash
reflect timeline                    # last 7 days
reflect timeline --days 14          # expand window
```

### When to use

- "Show me what happened this week."
- Auditing activity bursts vs quiet periods.

### When NOT to use

- For deep introspection of a single session — use `reflect sessions <id>`.

---

## Command: Improve

**Usage**: `/reflect improve`

Analyzes the knowledge base quality and proposes format.yaml changes.

### When to use

- The wiki feels noisy or sparse and you want config suggestions.
- After a few weeks of `reflect ingest` runs, to tune categories.

### When NOT to use

- Before any sessions have been ingested (nothing to analyze).

---

## Command: Metrics

**Usage**: `/reflect metrics`

Outputs quantitative health of the knowledge base.

### When to use

- Generating shields.io badges for the README (`--export badges/`).
- Weekly status updates — page counts, ingest cadence, etc.

### When NOT to use

- Replacement for `reflect status` (metrics are aggregate, status is current).

---

## Command: Init & Upgrade

```bash
reflect init                # scaffold .reflect/, install qmd, register collection
reflect init --no-wiki      # skip wiki layer
reflect init --migrate      # migrate from legacy harness
reflect upgrade             # update templates and agents to latest
```

### When to use

- First time setting up reflect in a repo (`init`).
- After upgrading the `reflect-cli` package and you want refreshed templates (`upgrade`).

### When NOT to use

- `init` in a repo that already has `.reflect/` — use `upgrade` to refresh templates instead.
- Never run `init` on a non-git directory; reflect needs git history.

### Common failures

- **qmd install fails**: `npm` may not be on PATH. Install qmd manually:
  `npm install -g @qubicfox/qmd-cli`.
- **Entire CLI install fails**: not fatal — reflect works in git-only mode.

---

## SessionStart Hook

If the hook output contains `REFLECT_WIKI_INGEST`, run `reflect ingest` to
update the knowledge base from new evidence. The hook fires when new sessions
or commits are detected since last ingest.

---

## Deep History: Keeper Agent

For questions that need deeper investigation than the wiki provides, spawn the
**Keeper** agent. Keeper follows an evidence ladder:

1. Search qmd for relevant wiki pages
2. Use `reflect search`, `reflect timeline`, `reflect sessions` for breadth
3. Drill into raw checkpoints with `entire explain --checkpoint <id>`
4. Cross-reference with `git log` and `git show`

Spawn Keeper when:
- You need to trace a decision across multiple sessions
- You want to understand what was tried vs what landed
- A pitfall entry needs verification before you proceed

---

## Rules

- NEVER read `.entire/metadata/` directly — use `reflect` CLI or `entire` CLI
- To customize knowledge categories, edit `.reflect/format.yaml`
- NEVER include secrets, API keys, or credentials in output
- **Pitfall entries are blocking**: if a past mistake is relevant to your
  current work, investigate before proceeding
- `src/reflect/_data/skill/SKILL.md` is the source of truth (in the reflect
  repo); `.claude/skills/reflect/SKILL.md` is the copy installed by `reflect init`.
