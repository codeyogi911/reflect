---
created: 2026-04-13
updated: 2026-04-13
sources: [checkpoint b2a5adf63dd2, checkpoint 4ecb34b81a12, checkpoint 9c595bc9b42d]
tags: [qmd, mcp, integration]
status: open
---

# Wire qmd MCP Server Integration

The qmd MCP server exists and is documented in reflect's skill, but is not yet wired into reflect's own agent tooling (checkpoint b2a5adf63dd2). The gap prevents reflect agents from using structured MCP calls for knowledge queries.

## Current State

The qmd npm package (`@tobilu/qmd`) ships with both a CLI and an MCP server. Reflect currently:
- Installs qmd automatically via `npm install -g @tobilu/qmd` during `reflect init` (checkpoint 4ecb34b81a12)
- Registers a qmd collection as `reflect-<repo-name>` for wiki indexing and semantic search
- Documents qmd's agentic flags (`--json`, `--files`, `--min-score`, `--all`, `--full`, `-n`, `--no-rerank`) in `skill/SKILL.md`
- References the MCP server option in skill documentation as an available resource

The keeper agent queries qmd via CLI invocation through `lib/search.py`, surfacing the fastest evidence rung in its ladder before descending to full session/git search (checkpoint b2a5adf63dd2).

## Gap: MCP Integration

The qmd MCP server is not registered in `.claude/agents/` or exposed as a tool to reflect's own agents. This means:
- The keeper agent cannot call qmd via structured MCP—it relies on CLI parsing
- Reflect agents cannot directly introspect qmd's collection state or use advanced query features through a standard MCP interface
- The skill documentation mentions the MCP option but reflect itself doesn't expose it to downstream agents

## Required Wiring

1. **MCP Server Registration**: Register the qmd MCP server in a `.claude/agents/` tool manifest or similar, exposing methods like `query`, `search`, `vsearch`, `embed`, `update`.
2. **Agent Access**: Update keeper agent (or new reflect-internal agents) to call qmd via MCP instead of shelling out to CLI.
3. **Structured Queries**: Use qmd's `--json` output format natively through MCP to receive ranked hits as structured data, eliminating regex parsing overhead.

## Reasoning

MCP integration allows reflect agents to treat qmd as a first-class tool with type-safe method calls, better error handling, and real-time collection state introspection—rather than parsing plain text CLI output. This aligns with reflect's v1.0.0 knowledge base architecture where agents self-serve queryable memory instead of receiving injected context.
