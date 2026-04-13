---
created: 2026-04-13
updated: 2026-04-13
sources: [checkpoint 4ecb34b81a12, checkpoint b2a5adf63dd2, checkpoint 9c595bc9b42d, checkpoint bdd0e5492e95]
tags: [qmd, installation, skill-setup, setup]
status: active
---

# qmd Installation and Skill Setup

qmd is the vector search and semantic indexing backend for reflect's knowledge base system. It is installed globally and registered as a Claude skill during `reflect init` with automatic collection creation. (checkpoint 4ecb34b81a12)

## Installation Command

Install qmd globally via npm or bun: (checkpoint 4ecb34b81a12)

```bash
npm install -g @tobilu/qmd
# or
bun install -g @tobilu/qmd
```

The package name is `@tobilu/qmd`.

## Skill Installation

During `reflect init`, the qmd skill is automatically installed via: (checkpoint b2a5adf63dd2)

```bash
qmd skill install --yes
```

This creates a symlink at `.claude/skills/qmd/` as a dedicated artifact separate from the `reflect` skill. (checkpoint 9c595bc9b42d) Both commands — the global package install and the skill install — are now part of `reflect init`'s standard workflow and are idempotent. (checkpoint 4ecb34b81a12)

## Collection Registration

When `reflect init` completes, it automatically registers a qmd collection named `reflect-<repo-name>` to avoid collisions across multiple repositories. (checkpoint 4ecb34b81a12) This collection is where all wiki content is indexed and made queryable.

## First-Run Behavior: llama.cpp Compilation

The first embed operation (vector indexing) compiles llama.cpp from source if no prebuilt binary is available, taking 5–10 minutes. (checkpoint bdd0e5492e95) Subsequent operations use the cached build and are much faster. The BM25 update step (`qmd update`) completes instantly. (checkpoint bdd0e5492e95)

## GPU / CPU Considerations

- node-llama-cpp auto-selects the Vulkan prebuilt when both Vulkan and CPU-only prebuilts are installed. (checkpoint 9c595bc9b42d)
- If the Vulkan SDK is absent, compilation fails. Explicitly remove the Vulkan package to force CPU-only operation. (checkpoint 9c595bc9b42d)
- Avoid running concurrent qmd processes during first-run setup — each triggers a duplicate llama.cpp compile. Kill redundant background jobs before shared build steps. (checkpoint bdd0e5492e95)

## Cleanup After State Wipe

If you completely reset `.reflect/`, stale qmd collections retain broken path references and must be explicitly removed. Delete orphaned collections from your local qmd registry when re-initializing a repository. (checkpoint 9c595bc9b42d)

## Integration with reflect Workflow

- `reflect init` now calls both `npm install -g @tobilu/qmd` and `qmd skill install --yes` automatically.
- After `reflect ingest`, the wiki is re-indexed via qmd update and embed.
- Agents query qmd directly via the installed skill rather than consuming injected context — this is the v1.0.0 architecture. (checkpoint 4ecb34b81a12)
