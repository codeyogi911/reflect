# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Repo-owned memory for AI coding agents. Reads raw evidence from Entire CLI sessions and git history on demand. Uses a declarative `format.yaml` to control what sections appear in context, and a Claude subagent to synthesize high-quality briefings with references. Generates context briefings (`context.md`) that any AI tool can read.

## Structure

- `reflect` — CLI entry point (Python)
- `lib/` — CLI modules (evidence, context, init, why, search, status, improve)
- `lib/evidence.py` — fixed evidence gathering pipeline (Entire CLI + git)
- `skill/SKILL.md` — skill source (dev copy; install copies to `.claude/skills/reflect/`)
- `SPEC.md` — specification for `.reflect/` directory format
- `hooks/session-start.sh` — SessionStart hook for context freshness (also linked from the skill dir)
- `install.sh` — installer (symlinks CLI to `~/.local/bin`)
- `README.md` — user-facing docs
- `ROADMAP.md` — future phases
- `CLAUDE.md` — this file

## Development

- Edit `lib/evidence.py` to change evidence gathering
- Edit `lib/context.py` to change synthesis pipeline, system prompt, or validation
- Edit `lib/` to change CLI commands
- Edit `.reflect/format.yaml` (in any repo) to customize context sections
- Edit `skill/SKILL.md` to change the Claude Code skill (source of truth)
- Test locally: `python3 reflect context` or `python3 reflect why <topic>`
- Install CLI via `./install.sh`; the skill is project-local under `.claude/skills/reflect/`

## Session Insights

- When writing code that shells out to external CLIs or APIs, verify available commands/endpoints with `--help` or reference docs before implementation — don't assume command signatures.
- For changes that affect core architecture (learning mechanism, data flow, required dependencies), confirm the design decision (optional vs required, additive vs replacement) with the user before implementing.

@.reflect/context.md
