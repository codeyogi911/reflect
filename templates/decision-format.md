# Decision Record Format Template

Use this format when writing decision records to `.reflect/decisions/`.

Filename convention: `<NNNN>-<slug>.md` (e.g., `0001-auth-strategy.md`)

---

```markdown
---
id: "<NNNN>"
title: <Short decision title>
date: <YYYY-MM-DD>
status: <proposed | accepted | superseded | deprecated>
sessions: [<session-id>, ...]
files: [<file-path>, ...]
superseded_by: <decision-id or null>
confidence: <HIGH | MEDIUM>
last_validated: <YYYY-MM-DD>
---

# Decision: <Title>

## Context
<What prompted this decision — the problem or constraint. 2-3 sentences.>

## Options Considered
1. **<Option A>** — <brief description> (CHOSEN)
2. **<Option B>** — <brief description>
3. **<Option C>** — <brief description>

## Decision
<Which option was chosen and why. 2-3 sentences focusing on the reasoning.>

## Consequences
- <Positive or negative consequence>
- <Trade-off accepted>
```

### Field Notes

- Only create decision records for **architectural or design choices** where alternatives were considered
- Do not create decisions for trivial implementation details
- **status**: `accepted` for active decisions, `superseded` when a later decision replaces it (set `superseded_by`), `deprecated` when the feature is removed
- **confidence**: `HIGH` if the decision has been validated by successful sessions, `MEDIUM` if new/untested
- **last_validated**: update this when a session confirms the decision still holds
- Decision IDs are sequential four-digit numbers: 0001, 0002, etc.
