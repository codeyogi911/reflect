# Insight Format Template

Use this format when writing insights to `.reflect/insights/`.

Filename convention: `<slug>.md` (e.g., `always-check-cli-help.md`)

---

```markdown
---
id: <slug>
title: <Short actionable title>
confidence: <LOW | MEDIUM | HIGH>
created: <YYYY-MM-DD>
last_seen: <YYYY-MM-DD>
times_seen: <N>
sessions: [<session-id>, ...]
category: <anti-pattern | best-practice | pitfall | workflow>
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
- **Freshness** is NOT stored — it's calculated at read time from `last_seen`:
  `freshness = 2^(-(days_since_last_seen / half_life_days))` where default half_life = 60 days
- **Promotion rules**:
  - Created at LOW: minor observation
  - Created at MEDIUM: caused failure or significant time sink
  - Promote to HIGH: seen in 2+ sessions, or caused 3+ retries, or confirmed a prior MEDIUM
- **Updating existing insights**: when a pattern recurs, update `last_seen`, increment `times_seen`, append to `sessions` list and Evidence Trail, promote confidence if warranted
- **baked**: set to true when the Actionable Rule has been written to a target file
