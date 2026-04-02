# File Knowledge Map Format Template

Use this format when writing file knowledge maps to `.reflect/files/`.

Filename convention: encode the file path by replacing `/` with `--` and append `.md`.
Example: `src/auth/middleware.ts` → `src--auth--middleware.ts.md`

---

```markdown
---
file: <original/file/path>
last_updated: <YYYY-MM-DD>
sessions: [<session-id>, ...]
decisions: [<decision-id>, ...]
insights: [<insight-slug>, ...]
change_frequency: <low | moderate | high>
---

# Knowledge: <original/file/path>

## What This File Does
<1-2 sentence description of the file's purpose, extracted from session context.>

## Key Facts
- <Important fact learned from sessions — e.g., "Token refresh logic is at line ~47">
- <Another fact — e.g., "The JWT library does NOT handle concurrent refresh natively">

## Common Pitfalls
- <Something to avoid when working with this file>

## Recent Changes
- <YYYY-MM-DD> (<session-id>): <What was changed and why>
```

### Field Notes

- **Path encoding**: `src/auth/middleware.ts` → filename `src--auth--middleware.ts.md`. Use `--` as separator because `/` cannot appear in filenames.
- Only create file knowledge maps for files that had **meaningful context** captured in a session — not every file touched
- **change_frequency**: based on how often the file appeared in sessions. `high` = 3+ sessions, `moderate` = 2 sessions, `low` = 1 session
- **Key Facts**: specific details that help future sessions (line numbers, implicit dependencies, non-obvious behavior)
- **Common Pitfalls**: things that caused issues in past sessions
- **Recent Changes**: keep the 5 most recent entries; older ones can be trimmed
- When updating an existing file map: merge new facts (don't duplicate), update `last_updated`, append session ID, update change_frequency
