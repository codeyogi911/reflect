# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Persistent, compounding knowledge base for any repository. Reads raw evidence from Entire CLI sessions and git history, extracts ALL knowledge worth remembering (decisions, preferences, patterns, gotchas, business rules, architecture, brand — anything discussed in sessions), and compiles it into a wiki at `.reflect/wiki/`. The wiki is indexed by qmd (required) for hybrid search (BM25 + vector + reranking). Agents query qmd directly for project memory — no context injection needed. The more sessions pile up, the more reflect knows.

## Structure

- `pyproject.toml` — package metadata, console script entry point (`reflect = reflect.cli:main`)
- `src/reflect/` — Python package (installed as `reflect-cli`)
  - `cli.py` — argparse dispatch, entry point
  - `__main__.py` — enables `python -m reflect`
  - `_version.py` — single source of truth for `__version__`
  - `evidence.py` — fixed evidence gathering pipeline (Entire CLI + git)
  - `wiki.py` — wiki layer utilities (frontmatter, page I/O, index scanning, index.md)
  - `ingest.py` — two-step wiki ingest (triage → write) + qmd re-indexing
  - `lint.py` — wiki health checks (stale, orphan, duplicate, coverage, resolved)
  - `context.py`, `init.py`, `search.py`, `status.py`, `sessions.py`, `timeline.py`, `improve.py`, `metrics.py` — subcommand implementations
  - `sources.py`, `fmt.py`, `aggregates.py` — shared helpers
  - `_data/` — package runtime data (copied into target repos on `reflect init`)
    - `_data/templates/` — `format.yaml` and `config.yaml` templates
    - `_data/skill/SKILL.md` — Claude Code skill source
    - `_data/skill/agents/keeper.md` — keeper subagent definition
    - `_data/hooks/session-start.sh` — SessionStart hook for knowledge base freshness
- `SPEC.md` — specification for `.reflect/` directory format
- `README.md` — user-facing docs
- `ROADMAP.md` — future phases
- `CLAUDE.md` — this file

## Development

- Install for development: `uv sync --all-extras` (creates editable install + dev + docs deps)
- Run the CLI: `uv run reflect <subcommand>` or activate the venv and use `reflect` directly
- Edit `src/reflect/evidence.py` to change evidence gathering
- Edit `src/reflect/context.py` to change synthesis pipeline, system prompt, or validation
- Edit `src/reflect/wiki.py` to change wiki utilities (frontmatter, page format, index.md)
- Edit `src/reflect/ingest.py` to change knowledge extraction (triage/write subagent prompts)
- Edit `src/reflect/lint.py` to change wiki health checks
- Edit `src/reflect/cli.py` to change CLI surface (flags, subcommand wiring)
- Edit `src/reflect/_data/templates/format.yaml` to change the default user-facing schema
- Edit `src/reflect/_data/skill/SKILL.md` to change the Claude Code skill (source of truth)
- Test locally: `uv run reflect status`
- Test wiki: `uv run reflect init && uv run reflect ingest --verbose && uv run reflect lint`
- Smoke test: `bash scripts/smoke.sh`

## Session Insights

- When writing code that shells out to external CLIs or APIs, verify available commands/endpoints with `--help` or reference docs before implementation — don't assume command signatures.
- For changes that affect core architecture (learning mechanism, data flow, required dependencies), confirm the design decision (optional vs required, additive vs replacement) with the user before implementing.
