# `.reflect/` Specification

**Version**: 4.0.0

This document specifies the `.reflect/` directory format — a minimal,
repo-owned interface for AI coding agent memory.

---

## 1. Design Principles

1. **Zero storage**: `.reflect/` does not duplicate evidence. It reads from
   Entire CLI and git on demand.
2. **Declarative format**: Context generation is controlled by `format.yaml`,
   not executable code. Users customize sections, not scripts.
3. **Subagent synthesis**: A Claude subagent distills raw evidence into
   context following the format config. Deterministic fallback when unavailable.
4. **Plug and play**: `reflect init` in any git repo. No external dependencies
   required (Entire CLI is optional enrichment, Claude CLI is optional synthesis).
5. **Human-reviewable**: All files are plain text. `format.yaml` is self-documenting.
6. **Agent-agnostic**: `context.md` is plain Markdown, readable by any tool.

---

## 2. Directory Layout

```
.reflect/
├── format.yaml         # Declarative section config (REQUIRED)
├── context.md          # Generated briefing for agent consumption (GENERATED)
├── config.yaml         # Optional operational configuration
├── .last_run           # Freshness state (GENERATED, gitignored)
└── wiki/               # Persistent knowledge base (OPTIONAL, committed)
    ├── decisions/      # Maps to "Key Decisions & Rationale" section
    ├── gotchas/        # Maps to "Gotchas & Friction" section
    ├── open-work/      # Maps to "Open Work" section
    ├── pitfalls/       # Maps to "Critical Pitfalls" section
    └── log.md          # Chronological ingest log
```

---

## 3. Format Config

The format config at `.reflect/format.yaml` declares what sections the
context briefing should contain. Each section has:

- **name**: Section heading in context.md
- **purpose**: One-line description (used as instruction for the subagent)
- **max_bullets**: Maximum items in this section
- **recency**: How far back to look for evidence (e.g., "7d", "30d")
- **entry_fields** (optional): List of required fields per bullet. The subagent
  must include each field in every entry. Use for structured sections like
  abandoned approaches where bare facts are insufficient.

Top-level keys:
- **citations**: `required` or `optional` — whether every bullet must have a reference
- **max_lines**: Total line budget for context.md

Example:
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
    purpose: "agent mistakes, reverted work, and failed approaches — each entry is a DON'T rule"
    max_bullets: 8
    recency: 90d
    entry_fields:
      - mistake         # what the agent did wrong
      - consequence     # what broke or had to be reverted
      - rule            # the "don't do X because Y" directive

citations: required
max_lines: 150
```

Users customize by editing section names, purposes, and counts. No code required.

---

## 4. Context Generation Pipeline

```
Evidence (fixed)          Format (user)           Synthesis
─────────────────         ──────────────          ─────────
Entire CLI sessions  ──►                    ──►   Claude subagent
Git history          ──►  format.yaml       ──►   (or deterministic
                          (sections, limits)       fallback)
                                                      │
                                                      ▼
                                                  context.md
```

1. **Evidence gathering** (fixed, internal): Reads recent checkpoints from
   Entire CLI and commits from git. Normalizes into a structured document.
2. **Synthesis** (subagent): Passes evidence + format config to Claude CLI.
   The subagent fills sections, includes references, respects limits.
3. **Validation**: Checks citations, line budget, section presence. Repairs
   missing citations where possible.
4. **Fallback**: If Claude CLI is unavailable, a deterministic renderer
   maps parsed checkpoint fields to sections.

---

## 5. Two Read Paths

### Passive (pre-session briefing)
`reflect context` writes `context.md`. When a wiki exists, this is a cheap
formatting pass over pre-synthesized wiki pages. Without a wiki, it runs the
full evidence → subagent pipeline. Use `--raw` to force raw synthesis.

### Active (live query)
`reflect search <query>` searches wiki pages first (when available), then
Entire CLI checkpoints and git history. Use `--wiki-only` to search only
pre-synthesized wiki knowledge. Results include source labels and citations.

---

## 6. Configuration

**Location**: `.reflect/config.yaml` (optional)

```yaml
max_lines: 150            # Line budget for context.md (overrides format.yaml)
session_start: auto       # "auto" regenerates on session start; "manual" reminds
auto_generate: true       # Allow Entire to generate missing AI summaries
```

---

## 7. Freshness Tracking

**Location**: `.reflect/.last_run` (generated, gitignored)

```json
{
  "last_checkpoint": "<entire-checkpoint-id>",
  "last_git_sha": "<short-sha>",
  "timestamp": "<ISO-8601>"
}
```

The session-start hook compares this against current state to decide whether
to regenerate context.md. When a wiki exists, the hook signals `REFLECT_WIKI_INGEST`
to run `reflect ingest` before `reflect context`, ensuring wiki pages are updated
from new evidence before the briefing is regenerated.

---

## 8. Wiki Layer (Optional)

The wiki layer adds persistent, compounding knowledge between raw evidence
and the bounded briefing. Enabled by default on `reflect init` (skip with `--no-wiki`).

### Page Format

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
- **status**: `active` (appears in briefings), `superseded`, or `resolved`
- **related**: cross-references to other wiki pages

### Operations

- **Ingest** (`reflect ingest`): Two-step subagent pipeline. Step 1 (triage):
  given new evidence + page index, produce a JSON plan of creates/updates/resolves.
  Step 2 (write): produce page content for each planned action.
- **Briefing** (`reflect context`): When wiki exists, generates context.md from
  wiki pages (cheap formatting pass, no LLM). Falls back to raw synthesis with `--raw`.
- **Search** (`reflect search`): Searches wiki pages first (text matching or qmd
  hybrid search), then Entire + git. `--wiki-only` skips raw sources.
- **Lint** (`reflect lint`): Health checks — stale pages, orphans, near-duplicates,
  coverage gaps, possibly-resolved open-work. `--fix` auto-resolves and archives.

### Directory Mapping

Each `format.yaml` section maps to a wiki subdirectory via slugification:
- "Key Decisions & Rationale" → `decisions/`
- "Gotchas & Friction" → `gotchas/`
- "Open Work" → `open-work/`
- "Critical Pitfalls" → `pitfalls/`

No separate index file — the index is built at runtime by scanning frontmatter.

---

## 9. Git Conventions

**Commit**: `.reflect/format.yaml`, `.reflect/config.yaml`, `.reflect/wiki/`
**Gitignore**: `.reflect/context.md`, `.reflect/.last_run`

---

## 10. Legacy Harness Escape Hatch

If `.reflect/harness` exists, `reflect context` runs it as a subprocess
instead of the format.yaml pipeline. This preserves backward compatibility
for repos with custom harness scripts. Migrate with `reflect init --migrate`.

---

## 11. Security

- Never store credentials, API keys, or secrets in context output.
- Evidence from session transcripts is treated as untrusted data in the
  subagent system prompt.

---

## Changelog

### 4.0.0 (2026-04-07)
- Architecture: added optional wiki layer (`.reflect/wiki/`) for persistent, compounding knowledge.
- Added: `reflect ingest` — two-step subagent pipeline (triage + write) for incremental wiki updates.
- Added: `reflect lint` — wiki health checks (stale, orphan, duplicate, coverage, resolved).
- Changed: `reflect context` now generates from wiki when available (cheap formatting, no LLM).
- Added: `--wiki` flag for `reflect init`, `--raw` for `reflect context`, `--wiki-only` for `reflect search`.
- Added: `lib/wiki.py` (foundation), `lib/ingest.py` (ingest), `lib/lint.py` (lint).
- Added: qmd integration for hybrid search (optional dependency).
- Wiki pages are committed to git; knowledge survives across sessions and team members.

### 3.0.0 (2026-04-04)
- Architecture: replaced executable harness with declarative `format.yaml`.
- Added: subagent synthesis via Claude CLI with deterministic fallback.
- Added: output validation (citations, line budget, section checks).
- Added: `reflect init --migrate` for harness → format.yaml migration.
- Legacy harness still supported as escape hatch.

### 2.0.0 (2026-04-03)
- Complete architecture redesign: zero storage, replaceable harness.
- Removed: artifact schemas, freshness decay model, confidence levels,
  contradiction handling, trace index, file knowledge maps.
- Added: harness contract, two read paths, freshness tracking.
- Evidence is read on demand from Entire CLI + git, not stored in `.reflect/`.
