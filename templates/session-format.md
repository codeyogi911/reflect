# Session Summary Format Template

Use this format when writing session summaries to `.reflect/sessions/`.

Filename convention: `YYYY-MM-DD_<session-id>.md`

---

```markdown
---
schema_version: "1.0"
session_id: <session-id>
date: <ISO-8601 timestamp>
branch: <git branch>
commits: [<commit-hash>, ...]
files_touched: [<file-path>, ...]
duration_estimate: <Nmin>
token_efficiency: <low | moderate | high>
outcome: <success | partial | failure>
---

# Session <session-id>: <one-line summary>

## Intent
<What the user was trying to accomplish — 1-2 sentences.>

## Outcome
<SUCCESS | PARTIAL | FAILURE>. <Brief description of end result.>

## Approach
1. <Step 1 — what was tried>
2. <Step 2>
3. ...

## Patterns Observed
- **<pattern-name>**: <description>

## Decisions Made
- DECISION_REF: <decision-id> (<brief description>)

## Key Context Captured
- `<file-path>`: <important fact learned about this file>
```

### Field Notes

- **token_efficiency**: `high` = few tokens per file changed, `moderate` = average, `low` = many retries/exploration
- **outcome**: `success` = task completed as intended, `partial` = partially done, `failure` = abandoned or reverted
- **commits**: empty list if no commits were made
- **Patterns Observed**: use short pattern IDs like `retry-loop`, `clean-first-pass`, `research-then-fail`
- **Decisions Made**: only include if an architectural/design decision was made; link to the decision record ID
- **Key Context**: facts about specific files that future sessions should know
