---
created: 2026-04-13
updated: 2026-04-13
sources: [checkpoint 4ecb34b81a12, checkpoint b2a5adf63dd2, checkpoint bdd0e5492e95, checkpoint 9c595bc9b42d]
tags: [init, qmd, setup, idempotent]
status: active
---

# reflect init Idempotent: qmd + Collection Setup

`reflect init` is idempotent and safely handles the complete qmd setup pipeline: npm installation, skill registration, and collection setup. It can be re-run on an already-initialized repo without side effects. (checkpoint 4ecb34b81a12)

## qmd npm Installation

During `reflect init`, qmd is installed globally as a required dependency via npm or bun:

```bash
npm install -g @tobilu/qmd
# or
bun install -g @tobilu/qmd
```

The npm package name is `@tobilu/qmd`. This installation is idempotent — running it multiple times simply upgrades or re-installs without error. (checkpoint 4ecb34b81a12)

## qmd Skill Installation

The qmd skill is installed as a dedicated artifact separate from the reflect skill itself:

```bash
qmd skill install --yes
```

This command creates a symlink at `.claude/skills/qmd/` and should be called during `reflect init`. The skill is installed to a distinct location rather than bundled with reflect, allowing it to be updated and versioned independently. (checkpoint b2a5adf63dd2)

## Collection Registration and Naming

Collections follow the naming convention `reflect-<repo-name>` to avoid collisions across multiple repos. During init, the collection is automatically registered and ready for indexing. (checkpoint 4ecb34b81a12)

Re-running `reflect init` on an already-initialized repo safely re-registers the collection without error. The collection registration is idempotent.

## Empty Wiki Guard

When the wiki is empty (no pages exist), `reflect init` skips the seed embed operation. This is a safety optimization: there is nothing to index, so qmd embed is not triggered. When pages are later added and ingested, qmd reindex runs automatically. (checkpoint 9c595bc9b42d)

## Idempotent Design

The entire flow is safe to re-run because:

1. **npm install** is idempotent — upgrading or reinstalling qmd causes no errors.
2. **qmd skill install** with `--yes` flag auto-accepts prompts and is idempotent.
3. **Collection registration** can be re-run without side effects; an existing collection is not duplicated.
4. **Empty wiki guard** prevents wasted embed cycles on zero-page wikis.

Testing on a pre-existing initialized repo confirms that re-running `reflect init` after skill changes or qmd upgrades is safe and predictable. (checkpoint 4ecb34b81a12)

## Gotcha: Stale Collection State

If the `.reflect/` directory is wiped manually but the qmd collection remains registered, the collection will retain broken path references. To fully reset:

1. Wipe `.reflect/` directory.
2. Explicitly remove the qmd collection registration (e.g., via `qmd collection delete reflect-<repo-name>` if such a command exists, or manually remove from qmd's state).
3. Re-run `reflect init` to re-register the collection cleanly.

Both the `.reflect/` directory and qmd collection state must be wiped independently; they do not automatically sync. (checkpoint 9c595bc9b42d)
