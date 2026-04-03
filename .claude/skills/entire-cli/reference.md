# Entire CLI — Architecture Reference

## Sessions & Checkpoints Domain Model

### Session

```go
type Session struct {
    ID          string       // "2025-12-01-<uuid>"
    Description string
    Strategy    string
    StartTime   time.Time
    Checkpoints []Checkpoint
}
```

### Checkpoint

```go
type Checkpoint struct {
    CheckpointID     id.CheckpointID // 12-hex-char stable identifier
    Message          string
    Timestamp        time.Time
    IsTaskCheckpoint bool            // Subagent vs session checkpoint
    ToolUseID        string          // For task checkpoints
}
```

### Checkpoint types

| Type | Location | Contents |
|------|----------|----------|
| Temporary | `entire/<hash>-<worktree>` shadow branch | Full state (code + metadata) |
| Committed | `entire/checkpoints/v1` branch (sharded) | Metadata + commit reference |

## Storage Layout

### Session state
`.git/entire-sessions/<id>.json` — active session tracking (shared across worktrees via git common dir).

### Temporary checkpoints (shadow branch)

```
<worktree files...>
.entire/metadata/<session-id>/
├── full.jsonl           # Complete transcript
├── prompt.txt           # Checkpoint-scoped user prompts
└── tasks/<tool-use-id>/ # Task checkpoints
```

Multiple concurrent sessions share the same shadow branch with metadata in separate subdirectories.

**Lifecycle:** Created on first checkpoint → migrated if HEAD changes → deleted after condensation → reset if orphaned.

### Committed checkpoints (`entire/checkpoints/v1`)

Sharded by checkpoint ID (first 2 chars = shard, remaining 10 = directory):

```
<id[:2]>/<id[2:]>/
├── metadata.json        # CheckpointSummary (aggregated)
├── 0/                   # First session (0-based)
│   ├── metadata.json    # Session-specific CommittedMetadata
│   ├── full.jsonl
│   ├── prompt.txt
│   └── content_hash.txt
├── 1/                   # Second session
└── 2/                   # Third session...
```

### Checkpoint ID linking

The ID creates a bidirectional link:

1. **User commit → Metadata:** Extract `Entire-Checkpoint: <id>` trailer, read tree at `<id[:2]>/<id[2:]>/`
2. **Metadata → User commits:** Search branch history for commits with matching trailer

## State Machine

```
[*] → IDLE (SessionStart)
IDLE → ACTIVE (TurnStart)
ACTIVE → IDLE (TurnEnd)
ACTIVE → ACTIVE (GitCommit/Condense)
IDLE → IDLE (GitCommit/Condense)
IDLE/ACTIVE → ENDED (SessionStop)
ENDED → ACTIVE (TurnStart — session resume)
ENDED → ENDED (GitCommit/CondenseIfFilesTouched)
```

## Checkpoint Scenarios

### Scenario 1: Normal flow
Prompt → agent changes → stop → user commits → PostCommit condenses → shadow deleted.

### Scenario 2: Agent commits mid-turn
Agent does `git commit` during ACTIVE phase → PostCommit saves provisional transcript → HandleTurnEnd finalizes with full transcript.

### Scenario 3: Multiple agent commits
Each commit gets unique checkpoint ID. All finalized together at turn end via `TurnCheckpointIDs`.

### Scenario 4: User splits into multiple commits
Content-aware carry-forward: uncommitted files get a new shadow branch. Each commit gets its own checkpoint.

### Scenario 7: Partial staging (`git add -p`)
Committed hash vs shadow hash comparison detects partial commits within a single file. Remaining hunks carried forward.

### Content-aware overlap detection
For new files: content hash must match shadow branch (prevents linking if user reverted and rewrote). For modified files: always counts as overlap.

## Attribution

Tracks agent vs. user contribution percentage using per-file pool heuristic:

1. **At prompt start** (`CalculatePromptAttribution`): capture user edits since last checkpoint
2. **At commit time** (`CalculateAttributionWithAccumulated`): sum accumulated user edits + post-checkpoint edits, subtract from total to get agent lines

LIFO assumption: users modify their own recent additions before touching agent code.

Result: `Entire-Attribution: 73% agent (146/200 lines)` trailer.

## Logging

Structured JSON logs to `.entire/logs/entire.log` using `log/slog`.

| Level | Purpose |
|-------|---------|
| DEBUG | Hook breadcrumbs, detailed diagnostics |
| INFO | Handler logs with full context |
| WARN | Non-blocking unexpected conditions |
| ERROR | Operation failures |

Configure: `ENTIRE_LOG_LEVEL=debug` env var or `log_level` in settings.

Hierarchical tracing: `session_id` (root) → `tool_use_id` (span) → `agent_id` (span metadata).

**Privacy rule:** Never log user prompts, task descriptions, file contents, or PII. Only log IDs, paths, timing, counts, and status.

```bash
# Filter by session
jq 'select(.session_id == "2025-12-31-abc123")' .entire/logs/entire.log

# Filter by subagent task
jq 'select(.tool_use_id == "X")' .entire/logs/entire.log
```

## Agent Implementation Guide

### Package structure

```
cmd/entire/cli/agent/youragent/
├── youragent.go          # Core Agent + init()
├── lifecycle.go          # ParseHookEvent + compile-time assertions
├── types.go              # Hook input structs, transcript types
├── hooks.go              # HookSupport (if applicable)
├── transcript.go         # TranscriptAnalyzer (if applicable)
└── *_test.go             # Tests
```

### Registration

```go
func init() {
    agent.Register("your-agent", NewYourAgent)
}
```

Add blank import in CLI command setup:
```go
import _ "github.com/entireio/cli/cmd/entire/cli/agent/youragent"
```

### ParseHookEvent — the main contribution surface

Map native hook names to normalized `EventType`. Return `nil, nil` for hooks with no lifecycle significance.

```go
func (a *YourAgent) ParseHookEvent(hookName string, stdin io.Reader) (*agent.Event, error) {
    switch hookName {
    case "session-start":
        raw, err := agent.ReadAndParseHookInput[sessionInfoRaw](stdin)
        if err != nil { return nil, err }
        return &agent.Event{
            Type: agent.SessionStart, SessionID: raw.SessionID,
            SessionRef: raw.TranscriptPath, Timestamp: time.Now(),
        }, nil
    case "prompt-submit":
        raw, err := agent.ReadAndParseHookInput[promptInputRaw](stdin)
        if err != nil { return nil, err }
        return &agent.Event{
            Type: agent.TurnStart, SessionID: raw.SessionID,
            SessionRef: raw.TranscriptPath, Prompt: raw.Prompt, Timestamp: time.Now(),
        }, nil
    case "response":
        raw, err := agent.ReadAndParseHookInput[sessionInfoRaw](stdin)
        if err != nil { return nil, err }
        return &agent.Event{
            Type: agent.TurnEnd, SessionID: raw.SessionID,
            SessionRef: raw.TranscriptPath, Timestamp: time.Now(),
        }, nil
    default:
        return nil, nil
    }
}
```

### Event field requirements

| Event | Required | Optional |
|-------|----------|----------|
| SessionStart | SessionID | SessionRef, ResponseMessage, Metadata |
| TurnStart | SessionID, SessionRef | Prompt, PreviousSessionID, Metadata |
| TurnEnd | SessionRef | SessionID (falls back to "unknown"), Metadata |
| Compaction | SessionID | SessionRef, Metadata |
| SessionEnd | SessionID | SessionRef, Metadata |
| SubagentStart | SessionID, SessionRef, ToolUseID | ToolInput, Metadata |
| SubagentEnd | SessionID, SessionRef, ToolUseID | SubagentID, ToolInput, Metadata |

### Transcript formats

| Format | Agents | Chunking | Position |
|--------|--------|----------|----------|
| JSONL | Claude Code, Factory AI Droid, Copilot CLI | `agent.ChunkJSONL` (newline boundaries) | Line count |
| JSON (messages array) | Gemini CLI, OpenCode | Split messages array across chunks | Message count |

### Hook config examples

**Claude Code** (`.claude/settings.json`):
```json
{"hooks": {"SessionStart": [{"matcher": "", "hooks": [{"type": "command", "command": "entire hooks claude-code session-start"}]}]}}
```

**Cursor** (`.cursor/hooks.json`):
```json
{"version": 1, "hooks": {"sessionStart": [{"command": "entire hooks cursor session-start"}]}}
```

**Gemini CLI** (`.gemini/settings.json`) — requires `hooksConfig.enabled: true` and `name` field.

**OpenCode** — uses a TypeScript plugin file (`.opencode/plugins/entire.ts`) instead of JSON.

### Hook installation principles

- Preserve unknown fields (don't destroy user's custom hooks)
- Idempotent installs (running twice doesn't duplicate)
- Support `localDev` mode with `go run "$(git rev-parse --show-toplevel)"/...`
- Identify Entire hooks by command prefix

### Compile-time assertions

```go
var (
    _ agent.TranscriptAnalyzer = (*YourAgent)(nil)
    _ agent.TokenCalculator    = (*YourAgent)(nil)
    _ agent.HookSupport        = (*YourAgent)(nil)
    _ agent.HookHandler        = (*YourAgent)(nil)
)
```

### Testing patterns

Test every hook name including pass-through (nil return), empty input, and malformed JSON.

Reference test files:
- `cmd/entire/cli/agent/claudecode/lifecycle_test.go`
- `cmd/entire/cli/agent/geminicli/lifecycle_test.go`
- `cmd/entire/cli/agent/cursor/lifecycle_test.go`
- `cmd/entire/cli/agent/opencode/lifecycle_test.go`
- `cmd/entire/cli/agent/factoryaidroid/lifecycle_test.go`

## External Agent Plugin Protocol

Standalone binaries matching `entire-agent-<name>` in `$PATH`. Protocol version: `1`.

### Environment

| Variable | Description |
|----------|-------------|
| `ENTIRE_REPO_ROOT` | Absolute path to git repo root |
| `ENTIRE_PROTOCOL_VERSION` | Protocol version (`1`) |

### Communication model
Subcommand-based, JSON over stdin/stdout, stateless, exit 0 = success.

### Required subcommands

| Subcommand | Purpose |
|------------|---------|
| `info` | Return agent metadata + capabilities JSON |
| `detect` | Check if agent is present (`{"present": true}`) |
| `get-session-id` | Extract session ID from HookInput (stdin) |
| `get-session-dir --repo-path <path>` | Session storage directory |
| `resolve-session-file --session-dir --session-id` | Session transcript path |
| `read-session` | Read session from HookInput (stdin) → AgentSession JSON |
| `write-session` | Write AgentSession (stdin) |
| `read-transcript --session-ref <path>` | Raw transcript bytes |
| `chunk-transcript --max-size <bytes>` | Split transcript → base64 chunks |
| `reassemble-transcript` | Reassemble base64 chunks → raw bytes |
| `format-resume-command --session-id <id>` | Resume command JSON |

### Capability-gated subcommands

| Capability | Subcommands |
|------------|-------------|
| `hooks` | `parse-hook`, `install-hooks`, `uninstall-hooks`, `are-hooks-installed` |
| `transcript_analyzer` | `get-transcript-position`, `extract-modified-files`, `extract-prompts`, `extract-summary` |
| `transcript_preparer` | `prepare-transcript` |
| `token_calculator` | `calculate-tokens` |
| `text_generator` | `generate-text` |
| `hook_response_writer` | `write-hook-response` |
| `subagent_aware_extractor` | `extract-all-modified-files`, `calculate-total-tokens` |

### Info response example

```json
{
  "protocol_version": 1,
  "name": "cursor",
  "type": "Cursor",
  "description": "Cursor - AI-powered code editor",
  "is_preview": true,
  "protected_dirs": [".cursor"],
  "hook_names": ["session-start", "session-end", "stop"],
  "capabilities": {
    "hooks": true,
    "transcript_analyzer": true,
    "transcript_preparer": false,
    "token_calculator": false,
    "text_generator": false,
    "hook_response_writer": false,
    "subagent_aware_extractor": false
  }
}
```

### Token usage format

```json
{
  "input_tokens": 1500,
  "cache_creation_tokens": 0,
  "cache_read_tokens": 200,
  "output_tokens": 500,
  "api_call_count": 3,
  "subagent_tokens": null
}
```

Only `input_tokens` and `output_tokens` are required. Optional fields default to `0`.

## Claude Code Hooks Deep Dive

Six hooks fire during a Claude Code session:

| Hook | Command | Trigger |
|------|---------|---------|
| SessionStart | `entire hooks claude-code session-start` | New chat begins |
| UserPromptSubmit | `entire hooks claude-code user-prompt-submit` | User submits prompt |
| Stop | `entire hooks claude-code stop` | Claude finishes responding |
| PreToolUse[Task] | `entire hooks claude-code pre-task` | Subagent about to start |
| PostToolUse[Task] | `entire hooks claude-code post-task` | Subagent finishes |
| PostToolUse[TodoWrite] | `entire hooks claude-code post-todo` | Subagent updates todo list |

### UserPromptSubmit details

1. Concurrent session check (blocks with warning if conflict)
2. Capture pre-prompt state (`git status` → untracked files snapshot)
3. Initialize session strategy (create/validate shadow branch)

### Stop details

1. Parse transcript (JSONL) — extract modified files from Write/Edit tool uses
2. Save metadata: `full.jsonl`, `prompt.txt`, `summary.txt`
3. Compute file changes: modified (transcript), new (untracked diff), deleted (git status)
4. Calculate token usage (deduplicated by message ID, includes subagent aggregation)
5. Call `strategy.SaveChanges()` → commit to shadow branch

### PostToolUse[TodoWrite] — incremental subagent checkpoints

Only fires inside subagent Task tool invocations. Creates checkpoint if files changed since last checkpoint, using last completed todo item as description.

```
PreToolUse[Task]       → (capture pre-task state only)
PostToolUse[TodoWrite] → Checkpoint #1: "Planning: 5 todos"
PostToolUse[TodoWrite] → Checkpoint #2: "Completed: Create user model"
PostToolUse[Task]      → Checkpoint #3: Final with all changes
```

## Integration Checklist

- [ ] Full transcript on every turn (not incremental diffs)
- [ ] Use agent's canonical export (native format preservation)
- [ ] No custom formats — store native format in NativeData
- [ ] Graceful degradation if canonical source unavailable
- [ ] `WriteSession` restores sessions for rewind/resume
- [ ] Map hooks to EventTypes: TurnStart, TurnEnd, SessionStart, SessionEnd
- [ ] Rewind restores full state; resume preserves session ID
- [ ] Test: new session, resumed session, rewind, agent shutdown
