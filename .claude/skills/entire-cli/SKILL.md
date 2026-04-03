---
name: entire-cli
description: Use and develop with the Entire CLI — a git-native tool that captures AI agent session transcripts, checkpoints, and attribution alongside commits. Covers day-to-day commands (enable, status, rewind, resume, explain, clean), configuration (settings, agents, checkpoint remotes, auto-summarization), security/redaction, troubleshooting, and building new agent integrations (Go Agent interface, ParseHookEvent, TranscriptAnalyzer, hook installation, external plugin protocol). Use when the user mentions Entire, entire enable, entire rewind, checkpoint, session transcript, agent integration, shadow branch, or AI session tracking.
---

# Entire CLI

Entire hooks into your git workflow to capture AI agent sessions as you work. Sessions are indexed alongside commits on a separate `entire/checkpoints/v1` branch, creating a searchable record of how code was written.

**Supported agents:** Claude Code, Gemini CLI, OpenCode, Cursor, Factory AI Droid, GitHub Copilot CLI.

## Quick Start

```bash
# Install
brew tap entireio/tap && brew install entireio/tap/entire
# Or: go install github.com/entireio/cli/cmd/entire@latest

# Enable in a repo
cd your-project && entire enable

# Check status
entire status
```

## Commands

| Command | Description |
|---------|-------------|
| `entire enable` | Install hooks for one or more agents |
| `entire disable` | Remove hooks |
| `entire status` | Show current session info |
| `entire rewind` | Restore code to a previous checkpoint |
| `entire resume <branch>` | Checkout branch, restore latest session, print continue command |
| `entire explain` | Show session or commit details (transcript, tokens, files) |
| `entire clean` | Clean orphaned data (`--all` for repo-wide, `--force` to delete) |
| `entire doctor` | Fix stuck sessions |
| `entire sessions stop` | Mark active sessions as ended |
| `entire login` | Device auth with Entire |

### `entire enable` flags

| Flag | Purpose |
|------|---------|
| `--agent <name>` | `claude-code`, `gemini`, `opencode`, `cursor`, `factoryai-droid`, `copilot-cli` |
| `--force` | Reinstall hooks |
| `--local` | Write to `settings.local.json` (gitignored) |
| `--skip-push-sessions` | Don't auto-push checkpoint branch |
| `--checkpoint-remote github:org/repo` | Push checkpoints to a separate repo |
| `--telemetry=false` | Disable anonymous analytics |

## Configuration

Two files in `.entire/`:

- **`settings.json`** — project-wide, committed to git
- **`settings.local.json`** — personal overrides, gitignored

| Option | Values |
|--------|--------|
| `enabled` | `true` / `false` |
| `log_level` | `debug`, `info`, `warn`, `error` |
| `strategy_options.push_sessions` | Auto-push `entire/checkpoints/v1` on git push |
| `strategy_options.checkpoint_remote` | `{"provider":"github","repo":"org/repo"}` |
| `strategy_options.summarize.enabled` | AI summary at commit time (requires `claude` CLI) |
| `telemetry` | Anonymous usage stats |

### Agent hook locations

| Agent | Config file |
|-------|-------------|
| Claude Code | `.claude/settings.json` |
| Gemini CLI | `.gemini/settings.json` |
| OpenCode | `.opencode/plugins/entire.ts` |
| Cursor | `.cursor/hooks.json` |
| Factory AI Droid | `.factory/settings.json` |
| Copilot CLI | `.github/hooks/entire.json` |

## Key Concepts

### Sessions
A unit of work with your AI agent. ID format: `YYYY-MM-DD-<uuid>`. Stored on `entire/checkpoints/v1`.

### Checkpoints
Point-in-time snapshots within a session (12-hex-char IDs). Created when you or the agent commit. Linked to user commits via `Entire-Checkpoint: <id>` trailer.

### Shadow branches
Temporary branches (`entire/<hash>-<worktree>`) holding full worktree snapshots + metadata during a session. Condensed to `entire/checkpoints/v1` on commit, then deleted.

### Attribution
`Entire-Attribution: 73% agent (146/200 lines)` trailer on commits. Uses per-file pool heuristic with LIFO assumption to separate agent vs. user contributions.

## Security & Privacy

- Transcripts are stored in your git repo on `entire/checkpoints/v1` — **visible to anyone with repo access**
- Automatic redaction (always on): entropy scoring + gitleaks pattern matching replaces detected secrets with `REDACTED`
- Shadow branches may contain **unredacted** data — never push them manually
- For sensitive repos, use a private repository or `--checkpoint-remote` to a private repo

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Shadow branch conflict | `entire clean --force` |
| Stuck session | `entire doctor` |
| SSH auth errors on resume | `ssh-keyscan -t rsa github.com >> ~/.ssh/known_hosts` |
| Debug mode | `ENTIRE_LOG_LEVEL=debug entire status` |
| Full cleanup | `entire clean --all --force` |

## Known Limitations

- `git commit --amend -m "..."` may lose `Entire-Checkpoint` trailer if no prior condensation exists and `/dev/tty` unavailable
- `git gc --auto` can corrupt worktree indexes when using shadow branches (fix: `git read-tree HEAD`; prevent: `git config gc.auto 0`)
- Concurrent ACTIVE sessions may produce spurious checkpoints (cosmetic only)

## Building Agent Integrations

For step-by-step implementation of a new agent, see [reference.md](reference.md).

### Architecture overview

Agents are passive data providers. The flow is:

```
Agent hook → ParseHookEvent() → Event → DispatchLifecycleEvent() → framework actions
```

Agents never call strategy methods directly — they only translate native hook payloads into normalized lifecycle events.

### Core Agent interface (19 methods)

| Group | Methods |
|-------|---------|
| Identity | `Name`, `Type`, `Description`, `DetectPresence`, `ProtectedDirs` |
| Events | `HookNames`, `ParseHookEvent` |
| Transcript | `ReadTranscript`, `ChunkTranscript`, `ReassembleTranscript` |
| Session | `GetHookConfigPath`, `SupportsHooks`, `ParseHookInput`, `GetSessionID`, `GetSessionDir`, `ResolveSessionFile`, `ReadSession`, `WriteSession`, `FormatResumeCommand` |

### Optional interfaces

| Interface | When to implement |
|-----------|-------------------|
| `HookSupport` | Agent uses a config file for hook registration |
| `HookHandler` | Required for `entire hooks <agent>` CLI subcommands |
| `TranscriptAnalyzer` | Transcript is parseable — extract file lists, prompts, summaries |
| `TranscriptPreparer` | Agent writes transcripts async (needs flush before read) |
| `TokenCalculator` | Transcript contains token usage data |
| `SubagentAwareExtractor` | Agent spawns subagents with separate transcripts |
| `HookResponseWriter` | Agent can display messages from hooks |
| `FileWatcher` | Agent doesn't support hooks; uses file-based detection |

### Event types

| Event | Purpose | Example agent hooks |
|-------|---------|---------------------|
| `SessionStart` | New session begins | `session-start` |
| `TurnStart` | User prompt submitted | `user-prompt-submit`, `before-agent` |
| `TurnEnd` | Agent finished responding | `stop`, `after-agent` |
| `Compaction` | Context window compressed | `pre-compress`, `pre-compact` |
| `SessionEnd` | Session terminated | `session-end` |
| `SubagentStart` | Subagent spawned | `pre-task`, `subagent-start` |
| `SubagentEnd` | Subagent completed | `post-task`, `subagent-stop` |

### Common pitfalls

- **Never use go-git v5 for checkout/reset** — it deletes untracked dirs even if gitignored
- **Always use `paths.RepoRoot()`** — `os.Getwd()` breaks from subdirectories
- **Implement `TranscriptPreparer`** if your agent writes transcripts async
- **`ParseHookEvent` returning `nil, nil`** is valid — means "no lifecycle action"
- **`AgentName`** is the registry key (`"claude-code"`); **`AgentType`** is the display name (`"Claude Code"`)

### External agent plugin protocol

Standalone binaries matching `entire-agent-<name>` in `$PATH` can integrate without modifying the CLI. Protocol is subcommand-based over stdin/stdout with JSON. See [reference.md](reference.md) for the full spec.
