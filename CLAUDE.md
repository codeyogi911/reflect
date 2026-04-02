# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A Claude Code skill called `/reflect` that builds dynamic repository knowledge from AI coding sessions. Analyzes transcripts to extract patterns, decisions, and insights, stores them in a structured knowledge base (`.reflect/`), and generates living context that makes every future session smarter. Powered by [Entire CLI](https://entire.io) for session capture.

## Structure

- `SKILL.md` — the skill definition file (frontmatter + workflow steps, all commands)
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
