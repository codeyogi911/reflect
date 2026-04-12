# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Persistent, compounding knowledge base for any repository. Reads raw evidence from Entire CLI sessions and git history, extracts ALL knowledge worth remembering (decisions, preferences, patterns, gotchas, business rules, architecture, brand — anything discussed in sessions), and compiles it into a wiki at `.reflect/wiki/`. The wiki is indexed by qmd (required) for hybrid search (BM25 + vector + reranking). Agents query qmd directly for project memory — no context injection needed. The more sessions pile up, the more reflect knows.

## Structure

- `reflect` — CLI entry point (Python)
- `lib/` — CLI modules (evidence, context, init, search, status, sessions, timeline, improve, metrics, ingest, lint, wiki)
- `lib/evidence.py` — fixed evidence gathering pipeline (Entire CLI + git)
- `lib/wiki.py` — wiki layer utilities (frontmatter, page I/O, index scanning, index.md)
- `lib/ingest.py` — two-step wiki ingest (triage → write) + qmd re-indexing
- `lib/lint.py` — wiki health checks (stale, orphan, duplicate, coverage, resolved)
- `skill/SKILL.md` — skill source (dev copy; install copies to `.claude/skills/reflect/`)
- `SPEC.md` — specification for `.reflect/` directory format
- `hooks/session-start.sh` — SessionStart hook for knowledge base freshness
- `install.sh` — installer (symlinks CLI to `~/.local/bin`)
- `README.md` — user-facing docs
- `ROADMAP.md` — future phases
- `CLAUDE.md` — this file

## Development

- Edit `lib/evidence.py` to change evidence gathering
- Edit `lib/context.py` to change synthesis pipeline, system prompt, or validation
- Edit `lib/wiki.py` to change wiki utilities (frontmatter, page format, index.md)
- Edit `lib/ingest.py` to change knowledge extraction (triage/write subagent prompts)
- Edit `lib/lint.py` to change wiki health checks
- Edit `lib/` to change CLI commands
- Edit `.reflect/format.yaml` (in any repo) to customize seed categories
- Edit `skill/SKILL.md` to change the Claude Code skill (source of truth)
- Test locally: `python3 reflect status` or `python3 reflect search <query>`
- Test wiki: `python3 reflect init && python3 reflect ingest --verbose && python3 reflect lint`
- Install CLI via `./install.sh`; the skill is project-local under `.claude/skills/reflect/`

## Session Insights

- When writing code that shells out to external CLIs or APIs, verify available commands/endpoints with `--help` or reference docs before implementation — don't assume command signatures.
- For changes that affect core architecture (learning mechanism, data flow, required dependencies), confirm the design decision (optional vs required, additive vs replacement) with the user before implementing.
