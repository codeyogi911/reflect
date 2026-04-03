# Benchmark Results

Self-benchmark: real Claude Code sessions solving tasks **with** vs **without** reflect context.
Each task runs in an isolated git worktree. An LLM checker scores the output.

## Overall

| | Count |
|---|---:|
| Tasks evaluated | 2 |
| Reflect wins | **2** |
| Baseline wins | 0 |
| Ties | 0 |
| Win rate | **100%** |
| Total cost | $0.73 |

## Results by Task

| Task | Difficulty | Baseline | Reflect | Delta | Winner | Run |
|---|---|---:|---:|---:|---|---|
| self-pitfall-001 | hard | 2.25 | 4.60 | +2.35 | **Reflect** | 2026-04-03_2234 |
| self-pitfall-001 | hard | 3.00 | 4.10 | +1.10 | **Reflect** | 2026-04-03_2244 |

## Task Details

### self-pitfall-001 (2026-04-03_2234)
**Add a reflect blame command that shows which sessions touched a file** — hard

| Metric | Baseline | Reflect |
|---|---:|---:|
| **Overall** | **2.25** | **4.60** |
| Correctness | 2/5 | 5/5 |
| Completeness | 3/5 | 4/5 |
| Code Quality | 2/5 | 5/5 |
| Awareness | 2/5 | 4/5 |
| Verdict | revise | accept |
| Turns | 7 | 8 |
| Cost | $0.1716 | $0.2026 |

**GT signals (Baseline):** 4/7 (57%)
- git log --follow present in blame.py
- get_checkpoint_for_commit called per commit
- list-based subprocess arguments used
- subcommand registered in reflect entry point following why/search pattern
- ~~sources.run not confirmed imported from sources.py~~
- ~~subprocess.run not directly called (task requires using sources helpers, not ...~~
- ~~shlex not explicitly used in blame.py (should flow through sources.run if pro...~~

**GT signals (Reflect):** 4/6 (67%)
- sources.run
- git log --follow
- get_checkpoint_for_commit
- list-based subprocess call
- ~~shlex~~
- ~~subprocess.run~~

> **Baseline:** The blame feature implementation is directionally correct but the agent caused serious collateral damage by deleting .reflect/harness and SKILL.md — critical project files unrelated to the task — which alone warrants revise regardless of the blame command quality. The ground truth requirement to use sources.py helpers also cannot be confirmed from the diff.

> **Reflect:** The implementation correctly satisfies every stated requirement: file argument, git log --follow traversal, per-commit checkpoint lookup, session intent display, and CLI registration following the why/search pattern. The two ground truth misses (shlex, subprocess.run) are non-issues in practice because list-based sources.run is the safer and idiomatic replacement. Code quality is clean with proper deduplication, graceful Entire-absent fallback, and consistent error return codes.

**Result: Reflect wins** (delta: +2.35)

---

### self-pitfall-001 (2026-04-03_2244)
**Add a reflect blame command that shows which sessions touched a file** — hard

| Metric | Baseline | Reflect |
|---|---:|---:|
| **Overall** | **3.00** | **4.10** |
| Correctness | 3/5 | 4/5 |
| Completeness | 4/5 | 5/5 |
| Code Quality | 2/5 | 4/5 |
| Awareness | 3/5 | 3/5 |
| Verdict | revise | accept |
| Turns | 9 | 9 |
| Cost | $0.2277 | $0.1300 |

**GT signals (Baseline):** 5/8 (62%)
- get_checkpoint_for_commit is called in lib/blame.py
- git log --follow used per transcript description
- sources.py helpers referenced in transcript
- blame subparser with file positional argument registered
- dispatch dict updated with blame command
- ~~Cannot verify subprocess.run is list-based in blame.py (full file not visible...~~
- ~~Cannot verify shlex is imported in blame.py~~
- ~~Cannot confirm sources.run is used rather than raw subprocess calls~~

**GT signals (Reflect):** 4/6 (67%)
- sources.run
- list-based subprocess args
- git log --follow
- get_checkpoint_for_commit
- ~~shlex~~
- ~~subprocess.run~~

> **Baseline:** The blame command logic that is visible (get_checkpoint_for_commit, session grouping, fallback behavior) looks correct and complete, but the agent committed the deletion of the core harness file — a destructive side effect that drops code quality to poor and makes the overall diff unsafe to accept as-is.

> **Reflect:** The implementation correctly addresses all four task requirements and follows project patterns cleanly; the only ground truth miss (shlex) is architecturally moot since list-based args are safer, and the transcript's awareness is adequate but shallow — it doesn't reference context.md history or prior decisions about sources.py design.

**Result: Reflect wins** (delta: +1.10)

---

## Run History

| Run | Mode | Model | Tasks | Cost |
|---|---|---|---:|---:|
| self-2026-04-03_2234 | self-bench-sandbox | claude-sonnet-4-6 | 1 | $0.37 |
| self-2026-04-03_2244 | self-bench-sandbox | claude-sonnet-4-6 | 1 | $0.36 |

---
*Generated from `python3 -m bench gen-report` — 2 runs, 2 task evaluations.*
