# Configuration

reflect is configured at three layers, all project-scoped:

1. **`.reflect/format.yaml`** — what categories the wiki has and how strict the
   triage subagent is.
2. **`.reflect/config.yaml`** — operational settings (e.g., `session_start: auto|manual`).
3. **Environment variables** — runtime knobs (model, budget, home).

There is **no global `~/.reflect/`**. Configuration travels with the repo.

## `.reflect/format.yaml`

The user-facing schema. Defines the wiki sections (categories), their recency
windows, and bullet limits. The triage subagent uses this as guidance but can
also propose new categories dynamically.

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
    purpose: agent mistakes, reverted work, and failed approaches
    max_bullets: 8
    recency: 90d
    entry_fields:
      - mistake       # what the agent did wrong
      - consequence   # what broke or had to be reverted
      - rule          # the "don't do X because Y" directive

citations: required
max_lines: 150
```

Field reference:

- `sections[].name` — display name (also drives the wiki subdirectory slug).
- `sections[].purpose` — guidance the LLM uses when deciding what fits.
- `sections[].max_bullets` — soft cap on entries per section in the briefing.
- `sections[].recency` — duration string (e.g. `30d`); pages older than this in
  this section are flagged stale by `reflect lint`.
- `sections[].entry_fields` — optional structured-bullet schema (e.g. for pitfalls).
- `citations` — `required` forces every bullet to cite a checkpoint/commit/file.
- `max_lines` — cap on the synthesized `context.md`.

## `.reflect/config.yaml`

Operational knobs:

```yaml
session_start: auto    # auto = SessionStart hook prints REFLECT_WIKI_INGEST
                       # manual = hook only prints a hint
```

## Environment variables

| Variable                  | Purpose                                          | Default                         |
|---------------------------|--------------------------------------------------|---------------------------------|
| `REFLECT_MODEL`           | Claude model for triage/write/context subagents  | `claude-haiku-4-5-20251001`     |
| `REFLECT_INGEST_BUDGET`   | USD ceiling per `reflect ingest` invocation      | `0.10`                          |
| `REFLECT_CONTEXT_BUDGET`  | USD ceiling per `reflect context` invocation     | `0.05`                          |
| `REFLECT_HOME`            | Override the reflect data directory              | unset                           |
| `QMD_LLAMA_GPU`           | Set to `false` on headless boxes (qmd CPU only)  | unset                           |

## Gitignore

`reflect init` will print a tip suggesting you add `.reflect/.last_run` to your
`.gitignore`. The rest of `.reflect/` (format, config, wiki pages, log.md,
index.md) is intended to be committed.
