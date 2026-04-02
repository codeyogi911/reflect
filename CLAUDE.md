# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A Claude Code skill called `/reflect` — portable, repo-owned memory for AI coding agents. Agent memory (Claude's `~/.claude/projects/`, Cursor's internal state) is machine-local and vendor-specific; `/reflect` puts memory in the repo instead. Entire CLI is the durable write-path and checkpoint substrate; `/reflect` reads from that substrate to extract decisions, failures, and working context. Stores interpretations in a structured knowledge base (`.reflect/`) and generates context overlays that make every future session smarter.

## Structure

- `SKILL.md` — the skill definition file (frontmatter + workflow steps, all commands)
- `SPEC.md` — agent-agnostic specification for the `.reflect/` evidence store format
- `templates/reflection-format.md` — output format for `.claude/reflections.md` (backward compat)
- `templates/session-format.md` — format for session summaries in `.reflect/sessions/`
- `templates/decision-format.md` — format for decision records in `.reflect/decisions/`
- `templates/insight-format.md` — format for insights in `.reflect/insights/`
- `templates/file-knowledge-format.md` — format for file knowledge maps in `.reflect/files/`
- `templates/context-format.md` — rules for generating `.reflect/context.md`
- `README.md` — installation and usage docs
- `CLAUDE.md` — this file
- `evals/evals.json` — skill evaluation test cases

## Development

- Edit `SKILL.md` to change the analysis workflow or add commands
- Edit `templates/` to change output formats for any artifact type
- Test locally by symlinking:
  ```bash
  mkdir -p ~/.claude/skills/reflect
  ln -sf $(pwd)/SKILL.md ~/.claude/skills/reflect/SKILL.md
  ln -sf $(pwd)/templates ~/.claude/skills/reflect/templates
  ```
- Invoke with `/reflect` in any project with Entire CLI sessions to test
- The skill reads templates at runtime, so changes to templates/ take effect immediately when symlinked

## Session Insights

- When writing code that shells out to external CLIs or APIs, verify available commands/endpoints with `--help` or reference docs before implementation — don't assume command signatures.
- For changes that affect core architecture (learning mechanism, data flow, required dependencies), confirm the design decision (optional vs required, additive vs replacement) with the user before implementing.
