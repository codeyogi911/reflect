# Insight Format Template

Use this format when writing insights to `.reflect/insights/`.

Filename convention: `<slug>.md` (e.g., `always-check-cli-help.md`)

---

```markdown
---
schema_version: "1.0"
id: <slug>
title: <Short actionable title>
confidence: <LOW | MEDIUM | HIGH>
created: <YYYY-MM-DD>
last_seen: <YYYY-MM-DD>
times_seen: <N>
sessions: [<session-id>, ...]
category: <anti-pattern | best-practice | pitfall | workflow | rejected-approach>
relevance_type: <temporal | architectural>
contradicts: <insight-slug or null>
contradicted_by: <insight-slug or null>
baked: <true | false>
baked_to: <CLAUDE.md or .claude/agents/{agent}.md or null>
---

# <Title>

## Pattern
<What keeps happening — 2-3 sentences describing the pattern with evidence.>

## Actionable Rule
<The specific instruction to follow — written as a clear directive that could
be pasted directly into CLAUDE.md or an agent file.>

## Evidence Trail
- **<YYYY-MM-DD> (<session-id>)**: <What happened in this session>
- **<YYYY-MM-DD> (<session-id>)**: <What happened>

## Promotion History
- <YYYY-MM-DD>: Created at <confidence> (<reason>)
- <YYYY-MM-DD>: Promoted to <confidence> (<reason>)
```

### Field Notes

- **Slug**: lowercase, hyphenated, descriptive (e.g., `test-before-refactor`, `verify-cli-flags`)
- **category**:
  - `anti-pattern`: something to avoid (retry loops, wrong assumptions)
  - `best-practice`: something that works well (test-first, focused investigation)
  - `pitfall`: a specific gotcha in the codebase (missing env file, implicit dependency)
  - `workflow`: a process improvement (run tests after auth changes, check CI before pushing)
  - `rejected-approach`: something that was tried and deliberately abandoned — negative memory to prevent re-attempts
- **relevance_type**:
  - `temporal` (default): normal freshness decay. For patterns tied to current tooling, dependencies, or transient conditions. Uses default half_life (60 days).
  - `architectural`: slow decay. For patterns tied to fundamental design choices, language constraints, or structural invariants. Uses half_life of 365 days.
- **Contradiction tracking**: when a new insight contradicts an existing one, set `contradicted_by: <new-slug>` on the old insight and `contradicts: <old-slug>` on the new one. A contradicted insight is excluded from context.md generation regardless of freshness.
- **Evidence weight**: insights that caused 3+ retries or disproportionate time sinks should be created at MEDIUM minimum, not LOW. Note retry count and estimated time cost in the Evidence Trail.
- **Freshness** is NOT stored — it's calculated at read time from `last_seen`:
  `freshness = 2^(-(days_since_last_seen / half_life_days))` where half_life depends on relevance_type (60 days for temporal, 365 days for architectural)
- **Promotion rules**:
  - Created at LOW: minor observation
  - Created at MEDIUM: caused failure or significant time sink
  - Promote to HIGH: seen in 2+ sessions, or caused 3+ retries, or confirmed a prior MEDIUM
- **Updating existing insights**: when a pattern recurs, update `last_seen`, increment `times_seen`, append to `sessions` list and Evidence Trail, promote confidence if warranted
- **baked**: set to true when the Actionable Rule has been written to a target file
