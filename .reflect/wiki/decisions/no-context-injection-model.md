---
created: 2026-04-13
updated: 2026-04-13
sources: [checkpoint 4ecb34b81a12, checkpoint b2a5adf63dd2]
tags: [architecture, qmd, agents, knowledge-base]
status: active
related: [decisions/wiki-layer-persistent-knowledge.md, decisions/keeper-agent-focused-design.md]
---

# No context.md Injection — Agents Query qmd

## The Decision

**Old model**: Reflect generated and injected a static `context.md` file into agent prompts at session start, containing the latest wiki snapshot.

**New model**: Agents are told "you have a qmd knowledge base collection; query it directly when you need context." No injection, no static file.

## Why

The old context.md injection approach had fundamental limits:

1. **Stale by design**: The injected context was a snapshot taken at session start. If the wiki grew during a session, agents couldn't access new information.
2. **Token budget pressure**: Larger wikis meant larger injected files, consuming precious context window for every session.
3. **Inflexible retrieval**: All agents got the same full context, regardless of relevance to their task.
4. **Decoupled from truth**: Agents read a generated artifact instead of querying the source directly.

The qmd self-serve model inverts this: agents query the live, indexed knowledge base on-demand, getting only what's relevant for their task. (checkpoint 4ecb34b81a12)

## How It Works

**Query Pattern**: Agents use the qmd CLI or MCP server to query the `reflect-<repo-name>` collection:

```bash
qmd query "<search term>" --json --min-score 0.6
```

The skill's SKILL.md explicitly directs agents to query rather than wait for injected context.

**Agentic Flags**: qmd exposes structured output flags for agent consumption (checkpoint b2a5adf63dd2):
- `--json`: Ranked hit list suitable for LLM consumption
- `--files`: Paths only, above a relevance floor
- `--full`: Complete document content
- `--min-score`: Relevance threshold

**Evidence Ladder**: The keeper agent queries qmd as the first rung of its evidence ladder (before broader session search or git history), making wiki knowledge the fastest, most reliable path. (checkpoint b2a5adf63dd2)

## Integration Points

1. **skill/SKILL.md**: Rewritten to direct agents to qmd queries instead of reading context.md.
2. **hooks/session-start.sh**: Simplified; no context generation step, only wiki ingest signal.
3. **lib/init.py**: Auto-installs qmd and registers the collection as `reflect-<repo>` during `reflect init`.
4. **lib/ingest.py**: Runs `qmd update` + `qmd embed` after every ingest to keep the index live.

## Pattern: When Agents Should Query

- **First**: Exact business logic, brand names, architectural decisions, past solutions → query qmd for direct hits
- **Then**: Broader session search or git history if qmd returns low confidence

Do not fall back to context.md injection; it does not exist. The qmd collection is the single source of truth for agent-accessible knowledge.

(checkpoint 4ecb34b81a12)
