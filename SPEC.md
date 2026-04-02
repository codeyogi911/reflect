# `.reflect/` Evidence Store Specification

**Version**: 1.0.0
**Status**: Draft

This document specifies the `.reflect/` directory format — a portable, repo-owned
knowledge store for AI coding agents. Any tool that reads or writes to `.reflect/`
should conform to this specification.

The spec is independent of any particular agent, skill, or session capture tool.
It defines the directory layout, artifact schemas, relationships between artifacts,
and the contract for generating a compiled context briefing.

---

## 1. Design Principles

1. **Repo-owned**: `.reflect/` lives in the repository root, versioned with git.
2. **Agent-agnostic**: Any compliant tool can read from and write to the store.
3. **Human-reviewable**: All artifacts are plain Markdown with YAML frontmatter.
4. **Constitution-respecting**: The project's human-authored instructions (e.g.,
   `CLAUDE.md`, `.cursorrules`, `copilot-instructions.md`) are the source of truth.
   Generated overlays from `.reflect/` supplement but never override them.
5. **Evidence-backed**: Every insight and decision traces back to session evidence.
6. **Decay-aware**: Temporal knowledge fades; architectural knowledge persists.

---

## 2. Directory Layout

```
.reflect/
├── index.md              # Master lookup table (REQUIRED)
├── context.md            # Compiled briefing (GENERATED, gitignored)
├── config.yaml           # Optional configuration overrides
├── sessions/             # Session evidence
│   └── YYYY-MM-DD_<session-id>.md
├── decisions/            # Architectural Decision Records
│   └── <NNNN>-<slug>.md
├── insights/             # Cross-session patterns
│   └── <slug>.md
├── files/                # File knowledge cache (convenience index)
│   └── <encoded-path>.md
└── history/              # Archived stale artifacts
```

### Artifact hierarchy

```
sessions  →  the raw evidence (what happened)
decisions →  durable choices extracted from sessions (what was decided)
insights  →  recurring patterns extracted from sessions (what was learned)
files     →  convenience index linking files to sessions/decisions/insights
context.md → compiled view for agent consumption (generated, not canonical)
```

**Decisions and insights are the durable primitives.** Sessions are evidence.
File maps are a derived convenience cache. `context.md` is a generated overlay.

---

## 3. Artifact Schemas

All artifacts use Markdown files with YAML frontmatter delimited by `---`.
Field names use `snake_case`. Dates use ISO 8601 (`YYYY-MM-DD`).

### 3.1 Session Summary

**Location**: `.reflect/sessions/YYYY-MM-DD_<session-id>.md`

#### Frontmatter

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | string | yes | `"1.0"` |
| `session_id` | string | yes | Unique session identifier |
| `date` | string | yes | ISO 8601 date or datetime |
| `branch` | string | no | Git branch name |
| `commits` | string[] | no | Commit hashes produced in this session |
| `files_touched` | string[] | no | File paths modified |
| `duration_estimate` | string | no | e.g., `"45min"` |
| `token_efficiency` | enum | no | `low` \| `moderate` \| `high` |
| `outcome` | enum | yes | `success` \| `partial` \| `failure` |

#### Body sections

| Section | Required | Description |
|---------|----------|-------------|
| Intent | yes | What the user was trying to accomplish (1-2 sentences) |
| Outcome | yes | Result status and brief description |
| Approach | no | Numbered steps of what was tried |
| Patterns Observed | no | Named patterns with descriptions |
| Decisions Made | no | References to decision record IDs |
| Key Context Captured | no | File-specific facts learned |

### 3.2 Decision Record

**Location**: `.reflect/decisions/<NNNN>-<slug>.md`

IDs are sequential four-digit numbers: `0001`, `0002`, etc.

#### Frontmatter

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | string | yes | `"1.0"` |
| `id` | string | yes | Four-digit sequential ID |
| `title` | string | yes | Short decision title |
| `date` | string | yes | ISO 8601 date |
| `status` | enum | yes | `proposed` \| `accepted` \| `superseded` \| `deprecated` |
| `sessions` | string[] | yes | Session IDs that informed this decision |
| `files` | string[] | no | File paths affected |
| `superseded_by` | string | no | ID of the replacing decision, or `null` |
| `confidence` | enum | yes | `HIGH` \| `MEDIUM` |
| `last_validated` | string | yes | ISO 8601 date of last confirmation |

#### Body sections

| Section | Required | Description |
|---------|----------|-------------|
| Context | yes | Problem or constraint (2-3 sentences) |
| Options Considered | yes | Numbered list with one marked `(CHOSEN)` |
| Decision | yes | What was chosen and why |
| Consequences | yes | Trade-offs accepted |

#### Lifecycle

- Decisions **do not decay**. An `accepted` decision remains valid until
  explicitly marked `superseded` or `deprecated`.
- When superseded, set `status: superseded` and `superseded_by: <new-id>`.
- Update `last_validated` when a session confirms the decision still holds.

### 3.3 Insight

**Location**: `.reflect/insights/<slug>.md`

Slugs are lowercase, hyphenated, descriptive (e.g., `verify-cli-flags`).

#### Frontmatter

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | string | yes | `"1.0"` |
| `id` | string | yes | Same as slug |
| `title` | string | yes | Short actionable title |
| `confidence` | enum | yes | `LOW` \| `MEDIUM` \| `HIGH` |
| `created` | string | yes | ISO 8601 date |
| `last_seen` | string | yes | ISO 8601 date of most recent occurrence |
| `times_seen` | integer | yes | Number of sessions exhibiting this pattern |
| `sessions` | string[] | yes | Session IDs where pattern was observed |
| `category` | enum | yes | See categories below |
| `relevance_type` | enum | yes | `temporal` \| `architectural` |
| `contradicts` | string | no | Slug of insight this contradicts, or `null` |
| `contradicted_by` | string | no | Slug of insight that supersedes this, or `null` |
| `baked` | boolean | yes | Whether the actionable rule has been exported |
| `baked_to` | string | no | Target file path, or `null` |

#### Categories

| Category | Description |
|----------|-------------|
| `anti-pattern` | Something to avoid |
| `best-practice` | Something that works well |
| `pitfall` | A specific gotcha in the codebase |
| `workflow` | A process improvement |
| `rejected-approach` | Tried and deliberately abandoned — negative memory |

#### Body sections

| Section | Required | Description |
|---------|----------|-------------|
| Pattern | yes | What keeps happening (2-3 sentences with evidence) |
| Actionable Rule | yes | Clear directive, suitable for pasting into instructions |
| Evidence Trail | yes | Dated entries with session IDs |
| Promotion History | no | Confidence level changes with dates and reasons |

#### Freshness model

Freshness is **calculated at read time**, never stored:

```
freshness = 2^(-(days_since_last_seen / half_life_days))
```

| `relevance_type` | `half_life_days` | Rationale |
|-------------------|-----------------|-----------|
| `temporal` | 60 | Tooling, dependencies, workarounds — transient |
| `architectural` | 365 | Design patterns, language constraints — durable |

Default freshness threshold for inclusion in `context.md`: **0.3**.

#### Confidence promotion

| Level | Criteria |
|-------|----------|
| `LOW` | Minor observation, uncertain pattern |
| `MEDIUM` | Seen once but caused failure or major time sink |
| `HIGH` | Seen in 2+ sessions, or 3+ retries, or promoted from MEDIUM on recurrence |

#### Contradiction handling

When a new insight contradicts an existing one:
1. Set `contradicted_by: <new-slug>` on the old insight.
2. Set `contradicts: <old-slug>` on the new insight.
3. A contradicted insight is **excluded from context.md** but **never deleted**.

### 3.4 File Knowledge Map

**Location**: `.reflect/files/<encoded-path>.md`

Path encoding: replace `/` with `--`, append `.md`.
Example: `src/auth/middleware.ts` → `src--auth--middleware.ts.md`

#### Frontmatter

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | string | yes | `"1.0"` |
| `file` | string | yes | Original file path |
| `last_updated` | string | yes | ISO 8601 date |
| `sessions` | string[] | no | Session IDs that touched this file |
| `decisions` | string[] | no | Decision IDs related to this file |
| `insights` | string[] | no | Insight slugs related to this file |
| `change_frequency` | enum | no | `low` \| `moderate` \| `high` |

#### Body sections

| Section | Required | Description |
|---------|----------|-------------|
| What This File Does | yes | 1-2 sentence purpose |
| Key Facts | no | Important details from sessions |
| Common Pitfalls | no | Things to avoid |
| Recent Changes | no | Last 5 changes with dates and session IDs |

File knowledge maps are a **convenience cache** — they are rebuilt from session
data and are not considered durable primitives. They may be deleted and
regenerated without data loss.

### 3.5 Index

**Location**: `.reflect/index.md`

The index is a master lookup table maintained alongside other artifacts.

#### Structure

```markdown
# Reflect Knowledge Index
<!-- Auto-maintained — do not rely on this for canonical data -->

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

## 4. Context Briefing Contract

**Location**: `.reflect/context.md`
**Lifecycle**: Generated, not hand-authored. Should be in `.gitignore`.

The context briefing is a compiled view of the most relevant current knowledge,
designed for agent consumption. Any compliant tool can generate it from the
typed records.

### 4.1 Generation rules

1. **Budget**: Maximum 150 lines (configurable via `config.yaml`).
2. **Full rewrite**: Regenerated from scratch each time, never appended.
3. **Constitution precedence**: If an entry conflicts with the project's
   human-authored instruction file, drop the entry.
4. **Self-contained**: No references that require reading other files.

### 4.2 Sections

| Section | Source | Max entries | Decay? |
|---------|--------|-------------|--------|
| Active Rules | Insights with confidence >= MEDIUM and freshness >= threshold | 15 | Yes |
| Key Decisions | Decisions with `status: accepted` | 10 | No |
| File Notes | File maps from last 5 sessions | 10 | By recency |
| Watch Out | Insights with `category: anti-pattern \| pitfall`, not baked | 5 | Yes |

Omit empty sections. Trim from the bottom of each section if over budget.

### 4.3 Entry format

Each Active Rules entry must include:
- The actionable rule text
- Confidence level
- Times seen
- Last seen date
- Approximate expiry date (when freshness will drop below threshold)

### 4.4 Output header

```markdown
# Dynamic Project Knowledge
<!-- GENERATED OVERLAY — computed from .reflect/ typed records -->
<!-- Human-authored project instructions always take precedence -->
<!-- Last updated: <ISO-8601 timestamp> -->
<!-- Source: <N> insights, <N> decisions, <N> file maps -->
```

---

## 5. Configuration

**Location**: `.reflect/config.yaml` (optional)

```yaml
# All fields are optional — defaults shown
max_lines: 150           # Line budget for context.md
half_life_days: 60       # Default half-life for temporal insights
freshness_threshold: 0.3 # Minimum freshness for context.md inclusion
```

---

## 6. Git Conventions

### Commit to version control
- `.reflect/index.md`
- `.reflect/sessions/`
- `.reflect/decisions/`
- `.reflect/insights/`
- `.reflect/files/`
- `.reflect/config.yaml`

### Add to `.gitignore`
- `.reflect/context.md` — generated overlay, regenerate locally

### Why commit the evidence store?

The value of repo-owned memory is that it travels with the code. When a new
contributor (human or agent) clones the repo, they inherit the project's
decision history, failure patterns, and accumulated insights. They can
regenerate `context.md` from the committed records.

---

## 7. Security

- **Never** store file contents, environment variable values, API keys, tokens,
  passwords, or credential-like strings in any artifact.
- If source evidence contains secrets, redact before writing. Use `[REDACTED]`.
- Artifact content should describe patterns and decisions, not reproduce code.

---

## 8. Size Budget

Total `.reflect/` directory should stay under **5 MB**. When approaching this
limit, archive stale artifacts to `.reflect/history/`. Stale means:
- Sessions older than 6 months with no linked active insights or decisions
- File maps for files that no longer exist in the repo
- Insights with freshness below 0.1

---

## 9. Schema Evolution

All artifacts include a `schema_version` field in frontmatter. The current
version is `"1.0"`.

When the schema changes:
1. Bump the version number.
2. Document changes in this spec.
3. Consumers should treat missing fields as optional (use defaults).
4. Consumers should ignore unrecognized fields (forward compatibility).

This follows a permissive evolution model: new fields can be added without
breaking existing consumers. Removing or renaming fields requires a major
version bump.

---

## 10. Implementing a Compliant Consumer

A minimal compliant **reader** must:
1. Parse YAML frontmatter from `.reflect/` Markdown files.
2. Respect the freshness model when filtering insights.
3. Respect contradiction exclusions (`contradicted_by` set → exclude).
4. Respect constitution precedence (human-authored instructions win).

A minimal compliant **writer** must:
1. Include `schema_version` in all frontmatter.
2. Assign session IDs and link artifacts via cross-references.
3. Never write secrets to artifacts.
4. Update `index.md` when creating new artifacts.

A compliant **context generator** must:
1. Follow sections 4.1–4.4 of this spec.
2. Calculate freshness at generation time, not store it.
3. Drop entries that conflict with the project's instruction file.
4. Stay within the configured line budget.

---

## Changelog

### 1.0.0 (2026-04-02)
- Initial specification extracted from `/reflect` skill implementation.
- Defines four artifact types: sessions, decisions, insights, file maps.
- Defines context briefing generation contract.
- Defines freshness decay model and contradiction handling.
- Adds `schema_version` field to all artifacts.
