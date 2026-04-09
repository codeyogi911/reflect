---
created: 2026-04-09
updated: 2026-04-09
sources: [commit 9cdf813, commit 7aa4e33, commit 1be188b]
tags: [pitfalls, context-pipeline, agents, decision]
status: active
---

# Critical Pitfalls Detection in Context Pipeline

## Motivation

Agents working with codebases need early, actionable awareness of project pitfalls—common mistakes, architectural constraints, and known failure modes—to avoid costly errors. Manual pitfall documentation is incomplete and stale. The Critical Pitfalls Detection feature (commit 9cdf813) automates identification and surfacing of project-specific pitfalls directly into the context pipeline, ensuring agents receive dynamic, session-aware warnings before attempting changes.

## Integration with Context Pipeline

This decision was implemented as part of the broader refactoring toward declarative, subagent-driven context generation (commit 7aa4e33). Rather than static docs, the system analyzes project state and prior evidence to systematically detect:

- Common architectural violations and antipatterns
- Patterns that have caused issues in previous sessions
- Configuration constraints and fragile dependencies
- Known regressions in specific code paths

Pitfalls are assembled into context during session start, enriching semantic context without requiring manual updates. This complements the wiki layer (commit 1be188b) by distinguishing persistent, compounding knowledge (wiki) from dynamic, task-aware pitfall warnings (context pipeline).

## Implementation Details

Detection logic integrates with the declarative `format.yaml` configuration system and the Claude subagent for context generation. When agents request context, the pipeline evaluates:

1. Prior checkpoint evidence and session history
2. Repository-specific patterns and failure modes  
3. Current codebase state and interdependencies

High-priority pitfalls are elevated to the top of context blocks, ensuring agents see warnings before proceeding with changes.

## Status

Active. Pitfalls detection is part of the standard context pipeline as of v0.6.0 and continues to evolve as more pitfall patterns are identified and catalogued across sessions.
