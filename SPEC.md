# `.reflect/` Specification

**Version**: 5.0.0

This document specifies the `.reflect/` directory format — a persistent,
compounding knowledge base for any repository.

---

## 1. Design Principles

1. **Sessions are the source**: All knowledge flows from coding sessions
   (Entire CLI transcripts) and git history. No external sources needed —
   if something matters, it came up in a session.
2. **Wiki compiles knowledge**: Raw session evidence is compiled into a
   structured wiki that compounds over time. The more sessions, the more
   reflect knows.
3. **qmd is the reader**: The wiki is indexed by qmd (hybrid BM25 + vector
   search). Agents query qmd directly — no context injection needed.
4. **Dynamic categories**: Wiki categories emerge from what the project
   actually discusses. Not limited to predefined sections.
5. **Human-reviewable**: All files are plain markdown. The wiki is browsable
   by humans and machines alike.
6. **Per-repo scope**: Each repo has its own knowledge base. User-level
   memory is handled by agent frameworks.

---

## 2. Directory Layout

```
.reflect/
├── format.yaml         # Declarative section config (REQUIRED)
├── config.yaml         # Optional operational configuration
├── .last_run           # Freshness state (GENERATED, gitignored)
└── wiki/               # Persistent knowledge base (committed)
    ├── index.md        # Auto-generated table of contents (committed)
    ├── log.md          # Chronological ingest log (committed)
    ├── _archive/       # Archived pages (superseded/resolved)
    ├── decisions/      # Why things are the way they are
    ├── gotchas/        # Things that burned time
    ├── pitfalls/       # Mistakes and failed approaches
    ├── open-work/      # Unfinished items
    ├── patterns/       # Coding patterns and conventions (dynamic)
    ├── preferences/    # User/team preferences (dynamic)
    ├── architecture/   # System structure and rationale (dynamic)
    ├── business/       # Domain/business knowledge (dynamic)
    └── <any-slug>/     # Categories created dynamically by triage
```

---

## 3. Format Config

The format config at `.reflect/format.yaml` declares seed categories and
context preferences. Categories are NOT limited to what's listed here —
the ingest triage agent can create new categories dynamically.

```yaml
sections:
  - name: Key Decisions & Rationale
    purpose: why things are the way they are, not what they are
    max_bullets: 8
    recency: 30d

  - name: Gotchas & Friction
    purpose: things that burned time or surprised the agent
    max_bullets: 6
    recency: 14d

  - name: Open Work
    purpose: unfinished items a new session should pick up
    max_bullets: 5
    recency: 7d

  - name: Critical Pitfalls
    purpose: agent mistakes, reverted work, and failed approaches
    max_bullets: 8
    recency: 90d

citations: required
max_lines: 150
```

---

## 4. Knowledge Extraction Pipeline

```
Sessions (Entire CLI)     Git History        format.yaml (seed categories)
──────────────────────    ────────────       ──────────────────────────────
     │                         │                          │
     └────────────┬────────────┘                          │
                  ▼                                       │
         Evidence Document                                │
                  │                                       │
                  ▼                                       ▼
         Triage Subagent ◄──── existing wiki index
                  │
                  ▼
          JSON Plan (create / update / resolve)
                  │
                  ▼
         Write Subagent (concurrent)
                  │
                  ▼
         .reflect/wiki/ pages + index.md
                  │
                  ▼
         qmd re-index (BM25 + vector embeddings)
```

The triage subagent extracts ALL knowledge from sessions:
- Decisions and their rationale
- Preferences and corrections
- Patterns and conventions
- Gotchas and friction
- Pitfalls and failed approaches
- Architecture and system design
- Business rules and domain knowledge
- Brand guidelines and style choices
- Deployment and operational guides
- Any other project-specific knowledge

Categories are dynamic — the triage agent proposes new categories
when knowledge doesn't fit existing ones. Directories are created
automatically.

---

## 5. Wiki Page Format

Each wiki page is a markdown file with YAML frontmatter:

```markdown
---
created: 2026-04-07
updated: 2026-04-07
sources:
  - checkpoint: abc123def456
  - commit: def789
tags: [architecture, format-yaml]
status: active
related:
  - decisions/zero-storage-architecture.md
---

# Page Title

Body text (200-500 words, synthesized knowledge with inline citations).
```

Frontmatter fields:
- **created/updated**: ISO dates for freshness tracking
- **sources**: provenance — checkpoint IDs or commit SHAs cited
- **tags**: 1-4 topic tags for filtering and search
- **status**: `active` (searchable), `superseded`, or `resolved`
- **related**: cross-references to other wiki pages

---

## 6. index.md

A committed table of contents, regenerated after every ingest. Groups
active pages by category with one-line summaries. Growth is managed by:
- `reflect lint --fix` archives resolved/superseded pages
- Archived pages are excluded from the index
- The triage agent prefers updating existing pages over creating duplicates

---

## 7. qmd Integration (Required)

qmd is the search backbone. The wiki is registered as a qmd collection
named `reflect-<directory-name>` to prevent collisions across repos.

```bash
# Registered automatically by reflect init
qmd collection add .reflect/wiki/ --name reflect-myapp

# Re-indexed automatically after every ingest
qmd update -c reflect-myapp && qmd embed -c reflect-myapp

# Agents query directly
qmd query "why do we use Supabase?" -c reflect-myapp
qmd search "brand colors" -c reflect-myapp
```

---

## 8. Operations

- **Ingest** (`reflect ingest`): Two-step subagent pipeline. Extracts all
  knowledge from new sessions/commits, updates wiki, re-indexes qmd.
- **Lint** (`reflect lint`): Health checks — stale, orphan, duplicate,
  coverage, resolved. `--fix` auto-archives and resolves.
- **Search** (`reflect search`): Text search across wiki + raw sources.
  For semantic search, use qmd directly.
- **Status** (`reflect status`): Evidence sources, wiki state, qmd health.

---

## 9. Configuration

**Location**: `.reflect/config.yaml` (optional)

```yaml
max_lines: 150            # Line budget for context.md (if generated)
session_start: auto       # "auto" ingests on session start; "manual" reminds
```

---

## 10. Freshness Tracking

**Location**: `.reflect/.last_run` (generated, gitignored)

```json
{
  "last_checkpoint": "<entire-checkpoint-id>",
  "last_git_sha": "<short-sha>",
  "timestamp": "<ISO-8601>"
}
```

The session-start hook compares this against current state to decide whether
to trigger `reflect ingest`.

---

## 11. Git Conventions

**Commit**: `.reflect/format.yaml`, `.reflect/config.yaml`, `.reflect/wiki/`
**Gitignore**: `.reflect/.last_run`

### Branch Policy

The wiki is **project memory** and should live on the default branch (`main`),
not on feature branches. This is the recommended workflow:

```
1. Develop on feature branches as usual — sessions accumulate in Entire CLI
2. Merge feature branch into main when ready
3. On main, run: reflect ingest
4. The wiki on main now reflects all evidence, including branch sessions
```

**Why this works:**
- Entire CLI checkpoints are stored globally, not per-branch. `reflect ingest`
  uses `entire explain --search-all` to pull checkpoints from any branch, so
  ingesting on main still captures conversations that happened on feature
  branches.
- Git history is fully visible from any branch ancestor, so commits made on
  feature branches are visible to the ingest pipeline once merged.

**Why not branch-local wikis:**
- Knowledge silos: pages on branch A don't appear on branch B
- Merge conflicts: `index.md` and shared pages conflict on every merge
- Stale qmd index: the index doesn't auto-rebuild on branch switch

**Guardrail**: `reflect ingest` prints a warning when run on a non-default
branch. Use `--force` to suppress it if you intentionally want a branch-local
wiki (e.g., for experimentation).

---

## 12. Security

- Never store credentials, API keys, or secrets in wiki pages.
- Evidence from session transcripts is treated as untrusted data in the
  subagent system prompt.

---

## Changelog

### 5.0.0 (2026-04-12)
- Vision: reflect is now a universal project knowledge base, not just session memory.
- Required: qmd is a required dependency (auto-installed by `reflect init`).
- Changed: Triage subagent extracts ALL knowledge from sessions (decisions,
  preferences, patterns, brand, business, etc.), not just coding signals.
- Added: Dynamic wiki categories — triage can create new categories on the fly.
- Added: Committed `index.md` — auto-generated table of contents.
- Added: Automatic qmd re-indexing after every ingest.
- Changed: Skill no longer injects context.md — agents query qmd directly.
- Changed: Session-start hook signals ingest only (no context generation).

### 4.0.0 (2026-04-07)
- Architecture: added optional wiki layer (`.reflect/wiki/`).
- Added: `reflect ingest`, `reflect lint`.
- Added: qmd integration for hybrid search (optional).

### 3.0.0 (2026-04-04)
- Architecture: replaced executable harness with declarative `format.yaml`.

### 2.0.0 (2026-04-03)
- Complete architecture redesign: zero storage, replaceable harness.
