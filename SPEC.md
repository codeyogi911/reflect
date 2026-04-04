# `.reflect/` Specification

**Version**: 3.0.0

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
└── .last_run           # Freshness state (GENERATED, gitignored)
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

  - name: Abandoned Approaches
    purpose: high-cost dead ends an agent would plausibly retry
    max_bullets: 5
    recency: 90d
    entry_fields:
      - approach        # what was tried
      - reason          # why it was abandoned
      - revisit_when    # condition for reconsidering, or "never"

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
`reflect context` runs the pipeline and writes `context.md`. This is the
pre-computed briefing that gets wired into instruction files (CLAUDE.md,
.cursorrules, etc.).

### Active (live query)
`reflect why <topic>` and `reflect search <query>` bypass the pipeline.
They fetch raw evidence from Entire + git and dump it to stdout. The agent
reasons over raw evidence — no line budget, no filtering.

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
to regenerate context.md.

---

## 8. Git Conventions

**Commit**: `.reflect/format.yaml`, `.reflect/config.yaml`
**Gitignore**: `.reflect/context.md`, `.reflect/.last_run`

---

## 9. Legacy Harness Escape Hatch

If `.reflect/harness` exists, `reflect context` runs it as a subprocess
instead of the format.yaml pipeline. This preserves backward compatibility
for repos with custom harness scripts. Migrate with `reflect init --migrate`.

---

## 10. Security

- Never store credentials, API keys, or secrets in context output.
- Evidence from session transcripts is treated as untrusted data in the
  subagent system prompt.

---

## Changelog

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
