# Reflect Roadmap

**`git` answers "what changed." `reflect` answers "why."**

---

## Current State (v4)

- A Python CLI + Claude Code skill
- Reads from Entire CLI + git on demand — zero intermediate storage
- Replaceable harness generates context briefings
- Two read paths: passive (context.md) and active (why/search dump raw evidence)
- Session-start hook with freshness tracking

**What works:** The read path architecture is clean. Harness is replaceable.
**What's missing:** Multi-tool wiring, community harnesses, team workflows.

---

## Phase 1: Universal Read Path

**Goal:** Any AI coding tool gets the briefing automatically.

Auto-wire `context.md` into every instruction file format:

| File | Tool |
|------|------|
| `CLAUDE.md` | Claude Code (done) |
| `.cursor/rules/*.mdc` | Cursor |
| `.github/copilot-instructions.md` | GitHub Copilot |
| `.windsurfrules` | Windsurf |
| `.clinerules` | Cline |

---

## Phase 2: Harness Ecosystem

**Goal:** Community-contributed harnesses for different use cases.

- `harness/default.py` — recency-ranked, ships with reflect
- `harness/semantic.py` — embedding-based retrieval
- `harness/summarizer.py` — LLM-powered session summarization
- `harness/legacy-v3.py` — implements the old confidence/decay model

Harness benchmarking: run two harnesses against the same evidence, compare context quality. This is the Meta-Harness optimization loop made accessible.

---

## Phase 3: Trust & Provenance

**Goal:** Safe multi-source evidence ingestion.

When reflect adds adapters for PRs, CI logs, Slack threads — trust matters:

| Source | Trust Level |
|--------|------------|
| Entire session (human-in-the-loop) | verified |
| Git commits | inferred |
| PR descriptions | inferred |

Trust boundaries prevent low-quality evidence from flowing into instruction
files. Deferred until multi-source adapters exist.

---

## Phase 4: Team Workflows

**Goal:** The "why" is shared across the team.

- GitHub Action on PR merge → captures decisions from PR description
- PR review bot → surfaces relevant evidence for changed files
- `reflect onboard` → generates comprehensive briefing for new contributors

---

## Phase 5: Harness Optimization

**Goal:** The harness improves itself.

The Meta-Harness paper shows that searching over harness implementations
outperforms hand-designed ones. With reflect's architecture:

1. Evidence filesystem exists (Entire + git)
2. Harness is a replaceable script
3. Evaluation signal exists (session outcomes, retry counts)
4. A proposer agent can rewrite the harness and measure results

This is the long game: reflect becomes the platform for automated harness
engineering.

---

## Priority Matrix

| Priority | Item | Effort | Impact |
|----------|------|--------|--------|
| **P0** | Multi-tool instruction file wiring | Small | Every AI tool benefits |
| **P1** | Harness ecosystem + benchmarking | Medium | Community contribution |
| **P1** | Additional evidence adapters (PRs, CI) | Medium | Richer evidence |
| **P2** | Trust & provenance model | Small | Enables safe multi-source |
| **P2** | Team workflows (GitHub Action, bot) | Medium | Team-level memory |
| **P3** | Harness optimization loop | Large | Self-improving memory |
