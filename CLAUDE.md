# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A Claude Code skill called `/reflect` that analyzes session transcripts to extract patterns (retry loops, research gaps, what worked, time sinks), produce structured reflections, and optionally bake validated insights into CLAUDE.md or agent files.

## Structure

- `SKILL.md` — the skill definition file (frontmatter + workflow steps)
- `templates/reflection-format.md` — the output format template for reflections
- `README.md` — installation and usage docs
- `CLAUDE.md` — this file
- `evals/evals.json` — skill evaluation test cases

## Development

- Edit `SKILL.md` to change the analysis workflow
- Edit `templates/reflection-format.md` to change the reflection output format
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
