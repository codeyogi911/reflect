# Wiki Layer for Reflect

Apply the [LLM Wiki](https://github.com/tobi/llm-wiki) pattern to reflect by adding a persistent wiki layer between raw evidence (Entire + git) and the bounded briefing (context.md). Knowledge compounds across sessions instead of being re-derived from scratch each time.

## The Problem

Reflect today works like RAG: every `reflect context` run gathers evidence from a bounded window (~12 checkpoints, ~20 commits), synthesizes from scratch, and overwrites `context.md`. Lessons older than the window are lost. A pitfall from three months ago that saved an agent 2 hours? Gone once it scrolls past the evidence horizon.

The SPEC.md (v3) explicitly embraces "zero storage" — read on demand, never persist distilled knowledge. This was the right call for v3, where the priority was simplicity. But it creates a ceiling: **reflect can't learn things it can't currently see.**

## The LLM Wiki Mapping

The wiki pattern has three layers. Two already exist in reflect:

- **Raw sources** = Entire CLI sessions + git history (unchanged, immutable)
- **Wiki** = `.reflect/wiki/` -- persistent, interlinked pages of distilled knowledge (NEW)
- **Schema** = `format.yaml` -- extended to define page types and wiki conventions (EVOLVED)
- **Briefing** = `context.md` -- now a generated view of the wiki, not the whole store (CHANGED)
- **Search** = qmd indexes the wiki for hybrid BM25 + vector + reranking search (NEW, Phase 2)

## Architecture

### Directory structure

```
.reflect/
  format.yaml              # Schema: sections become wiki categories
  config.yaml              # Operational config
  context.md               # Generated briefing (bounded, gitignored)
  .last_run                # Freshness state (gitignored)
  wiki/                    # Persistent knowledge base (NEW, committed)
    decisions/             # Maps to "Key Decisions & Rationale"
      declarative-format-yaml.md
      zero-storage-architecture.md
    pitfalls/              # Maps to "Critical Pitfalls"
      yaml-parser-state-reset.md
      markdown-fence-json-parsing.md
    gotchas/               # Maps to "Gotchas & Friction"
      entire-cli-hard-dependency.md
      dual-skillmd-sync.md
    open-work/             # Maps to "Open Work"
      decouple-entire-cli.md
    log.md                 # Chronological record of ingests
```

Note: no separate `index.md` file. The index is generated at read time by scanning frontmatter from wiki pages. This eliminates a merge-conflict surface (two developers running `reflect ingest` on different branches would both append to index.md) and removes a sync obligation. The wiki pages themselves are the source of truth.

### Page format

Each wiki page is a standalone markdown file with YAML frontmatter:

```markdown
---
created: 2026-04-04
updated: 2026-04-04
sources:
  - checkpoint: 68bae57a699d
  - commit: abc1234
tags: [architecture, format-yaml]
status: active          # active | superseded | resolved
related:
  - decisions/zero-storage-architecture.md
  - pitfalls/yaml-parser-state-reset.md
---

# Declarative format.yaml + Claude Subagent Synthesis

Replaced executable harness with format.yaml-driven context generation...
(2-5 paragraphs of synthesized knowledge, not raw dump)
```

Key properties:

- **sources** field preserves provenance (like citations in current context.md)
- **status** field: `active` pages appear in briefings, `superseded` ones are kept for history but deprioritized, `resolved` open-work items are archived
- **related** field: explicit cross-references (wikilinks)
- **tags**: enable filtering and category-based retrieval
- **Max page size**: ~500 words. Forces the subagent to synthesize rather than dump raw evidence. If a topic needs more, split into multiple linked pages.

### Git conventions

- **Commit**: `wiki/` directory and all pages — these are valuable accumulated knowledge
- **Gitignore**: `context.md`, `.last_run` — these are generated views (unchanged from v3)

This is the philosophical shift from v3: the wiki is worth committing because it represents distilled, human-reviewable knowledge that compounds.

### log.md format

Append-only, one entry per ingest. Each entry uses a consistent prefix for parseability:

```markdown
## [2026-04-07] ingest | 3 checkpoints, 8 commits
- Created: pitfalls/yaml-parser-state-reset.md
- Updated: decisions/declarative-format-yaml.md (added new evidence)
- Resolved: open-work/strip-markdown-fences.md
```

`log.md` is read by the ingest subagent to understand recent wiki activity (what was just processed, what changed recently). It's also useful for human audit — "when did the wiki learn about X?" Git history of individual pages provides per-page provenance, but the log provides the cross-cutting timeline view.

---

## Phased Implementation

### Phase 1: Wiki Foundation + Ingest + Briefing

**Goal**: Ship the compounding-knowledge loop. This is the highest-value change — everything else builds on it.

#### 1a. Wiki structure and init

- Add `reflect init --wiki` to create `wiki/` directory structure with subdirectories matching format.yaml sections
- Slugify section names for directory names (e.g., "Key Decisions & Rationale" → `decisions/`)
- Create empty `log.md`
- Update SPEC.md to v4 with wiki layer

#### 1b. Ingest command (`reflect ingest`)

The core new operation. This is where the LLM Wiki pattern's value lives.

**Flow**:

1. Gather evidence since last ingest (reuses existing `.last_run` state tracking)
2. Scan wiki page frontmatter to build an in-memory index of existing pages (title, status, tags, updated date)
3. Pass new evidence + in-memory index to Claude subagent in two steps:

**Step 1 — Triage**: Given new evidence and the page index, produce a structured plan:
- Which existing pages need updates (and why)
- Which new pages should be created (and in which category)
- Which pages should be marked superseded or resolved

**Step 2 — Write**: For each planned action, read the relevant existing page (if updating), and produce the new/updated page content.

Splitting triage from write keeps each subagent call focused and debuggable. The triage step is cheap (only reads the index, not full pages). The write step reads only the pages identified by triage.

4. Write pages to disk, update `log.md`
5. Update `.last_run` with new high-water marks

**Token budget**: The triage step sends the evidence + page index (titles and one-line summaries only). The write step sends evidence + the specific pages being updated (capped at 5 pages per call; if more need updating, batch into multiple calls). This keeps each call under ~20k tokens.

**First ingest**: Seeds the wiki from the full evidence window — equivalent to a current `reflect context` synthesis, but output goes to wiki pages instead of directly to context.md.

#### 1c. Briefing from wiki (`reflect context`)

Instead of synthesizing from raw evidence, `context.md` is generated from the wiki:

1. Scan wiki page frontmatter to find all active pages
2. Group pages by category (matching format.yaml sections)
3. Apply `recency` and `max_bullets` limits from format.yaml
4. Render `context.md` — this is a cheap formatting pass, not a synthesis. Each bullet summarizes one wiki page with a citation pointing to the page file.

This is much cheaper than today — the hard synthesis work is done during ingest. The briefing is just filtering and formatting.

**Fallback**: `reflect context --raw` preserves the current behavior (synthesize directly from evidence) for repos without a wiki or as an escape hatch.

#### 1d. Migration path

1. `reflect init --wiki` creates the wiki structure
2. First `reflect ingest` seeds the wiki from existing evidence
3. `reflect context` auto-detects `wiki/` and generates from it; falls back to raw synthesis if wiki doesn't exist
4. No flag needed — presence of `wiki/` directory is the signal

**Phase 1 deliverables**: `reflect init --wiki`, `reflect ingest`, updated `reflect context`, SPEC.md v4.

**Phase 1 status**: IMPLEMENTED (2026-04-07). Files: `lib/wiki.py` (foundation), `lib/ingest.py` (two-step ingest), updates to `lib/context.py`, `lib/init.py`, `reflect` CLI. Tested: init creates 4 category dirs, first ingest seeded 12 pages from evidence, second ingest triaged 2 creates + 2 updates, context generates from wiki in <1s with no LLM call. Checker-found bugs fixed: `action_type_eff` scoping, path traversal protection, path resolution mismatch, summary fallback, `.last_run` in wiki path.

---

### Phase 2: Enhanced Search (qmd integration)

**Goal**: Agents can ask semantic questions and get pre-synthesized answers from the wiki.

**Depends on**: Phase 1 (wiki must exist to search it).

#### 2a. Wiki-native search (no external deps)

Enhance `reflect search` to search wiki pages via simple text matching over page content and frontmatter. This replaces the current checkpoint+git grep with wiki grep — better signal because the pages are pre-synthesized.

Falls back to raw evidence search for recent sessions that haven't been ingested yet.

#### 2b. qmd integration (optional dependency)

[qmd](https://github.com/tobi/qmd) is a local markdown search engine with hybrid BM25 + vector + LLM reranking, all on-device.

- **Collection setup**: `reflect init --wiki` registers `.reflect/wiki/` as a qmd collection (`reflect-wiki`) if qmd is installed
- **Index maintenance**: After each `reflect ingest`, run `qmd update -c reflect-wiki && qmd embed`
- **Search**: `reflect search` delegates to qmd when available, falls back to text matching when not
- **MCP integration**: Agents with qmd's MCP server can search the wiki directly

**Why qmd specifically**:
- Hybrid search: BM25 catches exact terms ("format.yaml"), vector catches semantic queries ("why did we change the architecture"), reranking sorts by relevance
- On-device: No API keys, no external services. Aligns with reflect's local-first principle
- MCP server: Agents search the wiki as a native tool without reflect as intermediary
- Incremental: `qmd update` only re-indexes changed files

qmd is optional, following the same pattern as Entire CLI:
- With qmd: hybrid search with reranking
- Without qmd: text matching over wiki pages
- `reflect status` reports qmd availability

**Phase 2 deliverables**: Enhanced `reflect search` (wiki-native + qmd), qmd collection setup in `reflect init`.

**Phase 2 status**: IMPLEMENTED (2026-04-07). Wiki search with pre-filter optimization (check title/summary/tags before reading body). qmd fallback: if qmd returns empty, falls back to text search. `--wiki-only` flag. JSON output normalized to consistent shape. `reflect status` reports wiki page count and qmd availability. Checker fixes: error handling in page reads, qmd init return value check, wiki-not-found message for --wiki-only.

---

### Phase 3: Lint + Wiki Health

**Goal**: Keep the wiki healthy as it grows. Prevent bloat and staleness.

**Depends on**: Phase 1 (wiki must exist to lint it).

#### 3a. Lint command (`reflect lint`)

Periodic wiki health check:

- **Stale pages**: `updated` date older than category's `recency` window, newer evidence may have superseded them
- **Orphan pages**: no inbound `related` links from other pages
- **Missing pages**: concepts referenced in existing pages but lacking their own page
- **Contradictions**: pages that disagree with each other
- **Resolved open-work**: items that git history shows were completed
- **Coverage gaps**: format.yaml sections with few or no wiki pages

Output: a report with suggested actions. Optionally auto-fix with `--fix` (marks resolved items, suggests merges for near-duplicates).

#### 3b. Compaction strategy

Define when pages get archived or merged:

- Pages with `status: superseded` for >90 days → move to `wiki/_archive/`
- Pages with `status: resolved` for >30 days → move to `wiki/_archive/`
- Near-duplicate pages flagged by lint → suggest merge
- Category directories with >20 active pages → suggest splitting into subcategories

**Phase 3 deliverables**: `reflect lint`, `reflect lint --fix`, compaction rules, `_archive/` convention.

**Phase 3 status**: IMPLEMENTED (2026-04-07). Five checks: stale, orphan, possibly-resolved, coverage gaps, near-duplicates. --fix auto-resolves open-work and archives superseded pages. Non-zero exit for CI. Checker fixes: removed --oneline/--format conflict, keyword threshold bumped to 2 minimum, category check uses slugify().

---

## Key Design Decisions

### format.yaml sections become wiki categories

Each section in format.yaml maps to a wiki subdirectory. The `name` becomes the directory name (slugified), `purpose` guides the subagent during ingest, `max_bullets` controls the briefing view (not the wiki — the wiki can have unlimited pages per category), `recency` controls what appears in the briefing.

format.yaml doesn't need to change structurally — it gains a dual role: defining both wiki categories and briefing presentation.

### No separate index.md file

The in-memory index is built at runtime by scanning frontmatter. This avoids:
- Merge conflicts when multiple developers run ingest on different branches
- Sync bugs between index.md and actual page state
- An extra file to maintain

The cost is a directory scan + frontmatter parse on each ingest/context run. At wiki scale (~100s of pages), this is negligible.

### Ingest is two-step (triage then write)

A single "read evidence, update wiki" prompt is too much judgment for one subagent call. Splitting into triage (what to do) and write (do it) keeps each step focused, debuggable, and within a reasonable token budget. The triage output is also human-reviewable — you can see what the agent plans to do before it does it.

### The briefing is a lossy view

`context.md` is bounded (150 lines). The wiki is unbounded. The briefing is like `git log --oneline` — it shows the most relevant recent subset. An agent that needs deeper knowledge uses `reflect search` to query the wiki directly.

### What gets committed

The wiki (`wiki/`) is committed. This enables:
- Team members share accumulated knowledge
- Version history of knowledge evolution (via git)
- New contributors get the full knowledge base on clone
- The wiki survives `reflect init --reset`

## What This Unlocks

- **Compounding knowledge**: Lessons from month 1 survive to month 6
- **Cheaper synthesis**: Ingest is incremental; briefing is a cheap view over pre-synthesized pages
- **Semantic search** (Phase 2): Agents ask "why did we do X?" and get ranked, pre-synthesized answers
- **Team memory**: Committed wiki = shared knowledge base
- **Audit trail**: `log.md` + git history of wiki = full provenance of how knowledge evolved
- **Cross-project patterns** (future): Pages could link across repos or be templated

## What Stays the Same

- Evidence gathering pipeline (`lib/evidence.py`) — unchanged
- format.yaml structure and parsing — backward compatible
- Session-start hook (`hooks/session-start.sh`) — still drives freshness
- context.md format — agents see the same output
- Deterministic fallback — still works for repos without Claude CLI
- Optional dependencies pattern — qmd joins Entire CLI as optional enrichment
