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
reflect ingest --verbose            # show triage + write subagent progress
```

Ingests new evidence into the wiki via a two-step subagent pipeline:
1. **Triage**: Given new evidence + existing page index, produces a JSON plan.
   Extracts ALL knowledge: decisions, preferences, patterns, gotchas, pitfalls,
   architecture, business rules, brand guidelines — anything worth remembering.
   Can create new wiki categories dynamically.
2. **Write**: For each planned action, produces page content with frontmatter.
3. **Index**: Updates index.md and re-indexes the qmd collection.

Report the result: how many pages were created, updated, or resolved.

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

---

## Command: Status

**Usage**: `/reflect status`

Shows evidence source availability, wiki page count, qmd collection status,
and freshness state.

---

## Command: Sessions

**Usage**: `/reflect sessions [session_id]`

```bash
reflect sessions                    # list recent sessions
reflect sessions --limit 30         # show more
reflect sessions <session_id>       # inspect one session
```

---

## Command: Timeline

**Usage**: `/reflect timeline [--days N]`

```bash
reflect timeline                    # last 7 days
reflect timeline --days 14          # expand window
```

---

## Command: Improve

**Usage**: `/reflect improve`

Analyzes the knowledge base quality and proposes format.yaml changes.

---

## Command: Metrics

**Usage**: `/reflect metrics`

Outputs quantitative health of the knowledge base.

---

## Command: Init & Upgrade

```bash
reflect init                # scaffold .reflect/, install qmd, register collection
reflect init --no-wiki      # skip wiki layer
reflect init --migrate      # migrate from legacy harness
reflect upgrade             # update templates and agents to latest
```

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
- `skill/SKILL.md` is the source of truth; `.claude/skills/reflect/SKILL.md`
  is a copy installed by `reflect init`
