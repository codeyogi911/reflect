# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Repo-owned memory for AI coding agents. Reads raw evidence from Entire CLI sessions and git history on demand via a replaceable harness script. No intermediate storage — the harness fetches evidence at context-generation time. Generates context briefings (`context.md`) that any AI tool can read.

## Structure

- `reflect` — CLI entry point (Python)
- `lib/` — CLI modules (sources, context, init, why, search, status, note)
- `harness/default.py` — default harness script (reads Entire + git, writes context)
- `skill/SKILL.md` — skill source (dev copy; install copies to `.claude/skills/reflect/`)
- `SPEC.md` — specification for `.reflect/` directory format
- `hooks/session-start.sh` — SessionStart hook for context freshness (also linked from the skill dir)
- `install.sh` — installer (symlinks CLI to `~/.local/bin`)
- `README.md` — user-facing docs
- `ROADMAP.md` — future phases
- `CLAUDE.md` — this file

## Development

- Edit `harness/default.py` to change default context generation
- Edit `lib/` to change CLI commands
- Edit `skill/SKILL.md` to change the Claude Code skill (source of truth)
- Test locally: `python3 reflect context` or `python3 reflect why <topic>`
- Install CLI via `./install.sh`; the skill is project-local under `.claude/skills/reflect/`

## Session Insights

- When writing code that shells out to external CLIs or APIs, verify available commands/endpoints with `--help` or reference docs before implementation — don't assume command signatures.
- For changes that affect core architecture (learning mechanism, data flow, required dependencies), confirm the design decision (optional vs required, additive vs replacement) with the user before implementing.

@.reflect/context.md
