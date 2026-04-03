"""CLI entry point for the benchmark harness."""

import argparse
import json
import random
import sys
from pathlib import Path

from .config import BenchmarkConfig
from .tasks.registry import load_tasks


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def _truncate(text: str, max_lines: int = 50) -> str:
    """Truncate text to max_lines, showing a note if truncated."""
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text
    kept = lines[:max_lines]
    kept.append(f"  ... ({len(lines) - max_lines} more lines, see JSON for full output)")
    return "\n".join(kept)


def _indent(text: str, prefix: str = "  ") -> str:
    """Indent each line of text."""
    return "\n".join(prefix + ln for ln in text.splitlines())


def _score_bar(score: float, max_score: float = 5.0, width: int = 12) -> str:
    """Render a score as a visual bar: [████░░░░░░░░] 3.5/5"""
    filled = int(round(score / max_score * width))
    empty = width - filled
    return f"[{'█' * filled}{'░' * empty}] {score:.1f}/{max_score:.0f}"


def _diff_stat_summary(diff: str) -> str:
    """Extract just the file-level stat from a diff (files changed, insertions, deletions)."""
    if not diff or diff == "(no changes)":
        return "(no changes)"
    lines = diff.splitlines()
    # Find the stat summary line (e.g. "6 files changed, 66 insertions(+), 650 deletions(-)")
    for line in lines:
        stripped = line.strip()
        if "file" in stripped and "changed" in stripped and ("insertion" in stripped or "deletion" in stripped):
            return stripped
    # Fallback: count +/- lines in the full diff
    adds = sum(1 for ln in lines if ln.startswith("+") and not ln.startswith("+++"))
    dels = sum(1 for ln in lines if ln.startswith("-") and not ln.startswith("---"))
    files = set()
    for ln in lines:
        if ln.startswith("diff --git"):
            parts = ln.split()
            if len(parts) >= 4:
                files.add(parts[3])
    return f"{len(files)} file(s), +{adds} -{dels}"


def _files_touched(diff: str) -> list:
    """Extract list of files changed from a diff."""
    if not diff or diff == "(no changes)":
        return []
    files = []
    # Only look in the stat summary section (before "# Full Diff")
    stat_section = diff.split("# Full Diff")[0] if "# Full Diff" in diff else diff
    for line in stat_section.splitlines():
        stripped = line.strip()
        # Match stat lines like "lib/blame.py | 63 +++"
        # Must have a pipe, and the right side should be a number
        if "|" in stripped:
            parts = stripped.split("|", 1)
            fname = parts[0].strip()
            right = parts[1].strip()
            # Right side starts with a number (e.g. "63 +++") or "Bin"
            if fname and (right[:1].isdigit() or right.startswith("Bin")):
                files.append(fname)
    return files


def _wrap_text(text: str, width: int = 72, prefix: str = "    ") -> str:
    """Wrap text to width with prefix, respecting word boundaries."""
    import textwrap
    return textwrap.fill(text, width=width, initial_indent=prefix,
                         subsequent_indent=prefix)


def _print_session_comparison(task, without_session, with_session, without_checker, with_checker):
    """Print a clean, scannable comparison of two real sandbox sessions."""
    W = 72

    ws_a = without_checker.scores.weighted_score
    ws_b = with_checker.scores.weighted_score
    delta = ws_b - ws_a

    if delta > 0.1:
        verdict = "REFLECT WINS"
        verdict_icon = ">>>"
    elif delta < -0.1:
        verdict = "BASELINE WINS"
        verdict_icon = "<<<"
    else:
        verdict = "TIE"
        verdict_icon = "==="

    cost_total = without_session.cost_usd + with_session.cost_usd

    # ── Header ──────────────────────────────────────────────────────────
    print()
    print(f"  {'=' * W}")
    print(f"  {task.title}")
    print(f"  [{task.id}]  difficulty: {task.difficulty}  |  type: {task.type}")
    print(f"  {'=' * W}")

    # ── Verdict banner (top — the thing you want to see first) ─────────
    print()
    print(f"    {verdict_icon}  {verdict}  (delta: {delta:+.2f})  |  total cost: ${cost_total:.4f}")
    print()

    # ── Score comparison table ─────────────────────────────────────────
    sa = without_checker.scores
    sb = with_checker.scores
    print(f"    {'':22s} {'Baseline':>14s}    {'+ Reflect':>14s}")
    print(f"    {'─' * 56}")

    rows = [
        ("Overall",     sa.weighted_score,  sb.weighted_score,  5.0),
        ("Correctness", sa.correctness,     sb.correctness,     5.0),
        ("Completeness",sa.completeness,    sb.completeness,    5.0),
        ("Code Quality",sa.code_quality,    sb.code_quality,    5.0),
        ("Awareness",   sa.evidence_grounding, sb.evidence_grounding, 5.0),
    ]
    for label, va, vb, mx in rows:
        bar_a = _score_bar(va, mx)
        bar_b = _score_bar(vb, mx)
        marker = ""
        if label == "Overall":
            marker = "  ***"
        print(f"    {label:22s} {bar_a}    {bar_b}{marker}")

    # Verdict labels
    print(f"    {'':22s} {'(' + without_checker.verdict + ')':>14s}    {'(' + with_checker.verdict + ')':>14s}")

    # ── Session stats ──────────────────────────────────────────────────
    print()
    print(f"    {'':22s} {'Baseline':>14s}    {'+ Reflect':>14s}")
    print(f"    {'─' * 56}")
    print(f"    {'Turns':22s} {without_session.num_turns:>14d}    {with_session.num_turns:>14d}")
    tok_a = without_session.input_tokens + without_session.output_tokens
    tok_b = with_session.input_tokens + with_session.output_tokens
    print(f"    {'Tokens':22s} {tok_a:>14,d}    {tok_b:>14,d}")
    print(f"    {'Cost':22s} {'${:.4f}'.format(without_session.cost_usd):>14s}    {'${:.4f}'.format(with_session.cost_usd):>14s}")

    has_diff_a = without_session.diff and without_session.diff != "(no changes)"
    has_diff_b = with_session.diff and with_session.diff != "(no changes)"

    if without_session.is_error:
        print(f"    {'Error':22s} {without_session.error_message[:30]:>14s}    {'—':>14s}")
    if with_session.is_error:
        print(f"    {'Error':22s} {'—':>14s}    {with_session.error_message[:30]:>14s}")

    # ── Files touched (compact) ────────────────────────────────────────
    files_a = _files_touched(without_session.diff)
    files_b = _files_touched(with_session.diff)

    print()
    print(f"    Files changed:")
    print(f"      Baseline   ({_diff_stat_summary(without_session.diff)})")
    for f in files_a:
        print(f"        {f}")
    if not files_a:
        print(f"        (none)")

    print(f"      + Reflect  ({_diff_stat_summary(with_session.diff)})")
    for f in files_b:
        print(f"        {f}")
    if not files_b:
        print(f"        (none)")

    # ── Ground truth coverage ──────────────────────────────────────────
    print()
    for label, checker in [("Baseline", without_checker), ("+ Reflect", with_checker)]:
        hits = checker.ground_truth_hits
        misses = checker.ground_truth_misses
        total = len(hits) + len(misses)
        cov = len(hits) / total if total else 0
        # Short signal names only
        hit_short = [h.split(" — ")[0].split(" ")[0] if " — " in h or len(h) > 40 else h for h in hits]
        miss_short = [m.split(" — ")[0].split(" ")[0] if " — " in m or len(m) > 40 else m for m in misses]
        print(f"    GT signals ({label}): {len(hits)}/{total} ({cov:.0%})")
        if hit_short:
            print(f"      hit:  {', '.join(hit_short)}")
        if miss_short:
            print(f"      miss: {', '.join(miss_short)}")

    # ── Checker rationale (concise) ────────────────────────────────────
    print()
    for label, checker in [("Baseline", without_checker), ("+ Reflect", with_checker)]:
        if checker.rationale:
            print(f"    Rationale ({label}):")
            print(_wrap_text(checker.rationale[:250], width=W, prefix="      "))
            print()

    # ── Agent reasoning (collapsed, short) ─────────────────────────────
    print(f"    Agent summaries:")
    for label, session in [("Baseline", without_session), ("+ Reflect", with_session)]:
        print(f"      [{label}]")
        if session.transcript:
            # Show first ~8 lines only
            excerpt = "\n".join(session.transcript.splitlines()[:8])
            print(_indent(excerpt, "        "))
            remaining = len(session.transcript.splitlines()) - 8
            if remaining > 0:
                print(f"        ... ({remaining} more lines in JSON)")
        else:
            print("        (no transcript)")
        print()

    print(f"  {'=' * W}")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_self_bench(args):
    """Run the self-benchmark: real Claude Code sessions with vs without reflect."""
    from .sandbox import (
        create_worktree, cleanup_worktree,
        setup_worktree_without_reflect, setup_worktree_with_reflect,
        run_session,
    )
    from .loop.checker import CheckerAgent

    repo_path = args.repo or str(Path(__file__).parent.parent)

    config = BenchmarkConfig(
        target_repo=repo_path,
        v3_reflect_dir="",
        maker_model=args.model,
        checker_model=args.model,
        max_rounds=1,  # single session per version (real coding, not iteration)
        tasks_file=args.tasks,
        dry_run=args.dry_run,
    )

    all_tasks = load_tasks(config.tasks_file)

    # Task selection
    if args.quick:
        if args.task:
            matches = [t for t in all_tasks if t.id == args.task or args.task.lower() in t.id.lower()]
            if not matches:
                print(f"Task not found: {args.task}", file=sys.stderr)
                print(f"Available: {', '.join(t.id for t in all_tasks)}", file=sys.stderr)
                return 1
            tasks = [matches[0]]
        else:
            tasks = [random.choice(all_tasks)]
        print(f"Quick benchmark: 1 task ({tasks[0].id}), model={args.model}")
    else:
        tasks = all_tasks
        if args.task:
            matches = [t for t in all_tasks if args.task.lower() in t.id.lower()]
            if not matches:
                print(f"Task not found: {args.task}", file=sys.stderr)
                return 1
            tasks = matches
        print(f"Self-benchmark: {len(tasks)} tasks, model={args.model}")

    results_dir = Path("bench/results") / f"self-{config.run_id}"
    results_dir.mkdir(parents=True, exist_ok=True)
    tasks_dir = results_dir / "tasks"
    tasks_dir.mkdir(exist_ok=True)

    with open(results_dir / "run_config.json", "w") as f:
        json.dump({
            **config.to_dict(),
            "mode": "self-bench-sandbox",
            "quick": args.quick,
            "task_ids": [t.id for t in tasks],
            "max_budget_per_session": args.max_budget,
        }, f, indent=2)
    print(f"Results: {results_dir}")
    print(f"Budget per session: ${args.max_budget:.2f}")

    if config.dry_run:
        print(f"\n--- Dry Run: Would create worktrees and run {len(tasks)} task(s) ---")
        for task in tasks:
            print(f"  {task.id}: {task.title}")
            print(f"    Type: {task.type} | Difficulty: {task.difficulty}")
            print(f"    Files: {task.relevant_files}")
            print(f"    GT signals: {task.ground_truth_signals}")
        print(f"\nWould create 2 worktrees per task in /tmp/reflect-bench/")
        print(f"Dry run complete. No API calls or worktrees created.")
        return 0

    checker = CheckerAgent(config)
    total_tasks = len(tasks)
    all_results = []

    for i, task in enumerate(tasks, 1):
        print(f"\n  --- [{i}/{total_tasks}] {task.id} ---")

        task_results = {}

        for label, setup_fn in [("without", setup_worktree_without_reflect), ("with", setup_worktree_with_reflect)]:
            wt_name = f"{config.run_id}-{task.id}-{label}"
            wt_path = None
            print(f"\n  [{label}-reflect] Creating worktree...")

            try:
                wt_path = create_worktree(repo_path, wt_name)
                print(f"  [{label}-reflect] Worktree: {wt_path}")

                # Set up the worktree for this mode
                setup_fn(wt_path)

                # Run the real session
                print(f"  [{label}-reflect] Running Claude Code session...")
                session = run_session(
                    worktree_path=wt_path,
                    prompt=task.prompt,
                    model=args.model,
                    max_budget_usd=args.max_budget,
                    with_reflect=(label == "with"),
                )

                if session.is_error:
                    print(f"  [{label}-reflect] SESSION ERROR: {session.error_message}", file=sys.stderr)
                else:
                    has_diff = session.diff and session.diff != "(no changes)"
                    print(f"  [{label}-reflect] Done: {session.num_turns} turns, ${session.cost_usd:.4f}, changes={'yes' if has_diff else 'no'}")

                # Checker evaluates the diff
                print(f"  [{label}-reflect] Checking...")
                checker_resp = checker.evaluate(task, session.diff, session.transcript)
                print(f"  [{label}-reflect] Verdict: {checker_resp.verdict} (score={checker_resp.scores.weighted_score:.2f})")

                task_results[label] = {"session": session, "checker": checker_resp}

                # Save detailed results
                with open(tasks_dir / f"{task.id}_{label}.json", "w") as f:
                    json.dump({
                        "task_id": task.id,
                        "version": f"{label}-reflect",
                        "diff": session.diff,
                        "transcript": session.transcript,
                        "cost_usd": session.cost_usd,
                        "input_tokens": session.input_tokens,
                        "output_tokens": session.output_tokens,
                        "num_turns": session.num_turns,
                        "is_error": session.is_error,
                        "error_message": session.error_message,
                        "checker_verdict": checker_resp.verdict,
                        "checker_scores": checker_resp.scores.to_dict(),
                        "checker_rationale": checker_resp.rationale,
                        "ground_truth_hits": checker_resp.ground_truth_hits,
                        "ground_truth_misses": checker_resp.ground_truth_misses,
                    }, f, indent=2)

            except Exception as e:
                print(f"  [{label}-reflect] FAILED: {e}", file=sys.stderr)

            finally:
                # Always clean up the worktree
                if wt_path:
                    print(f"  [{label}-reflect] Cleaning up worktree...")
                    cleanup_worktree(repo_path, wt_path)

        # Print comparison if we have both results
        if "without" in task_results and "with" in task_results:
            _print_session_comparison(
                task,
                task_results["without"]["session"],
                task_results["with"]["session"],
                task_results["without"]["checker"],
                task_results["with"]["checker"],
            )
            all_results.append(task_results)

    # --- Summary ---
    if all_results:
        wins_a, wins_b, ties = 0, 0, 0
        total_cost = 0
        for tr in all_results:
            wa = tr["without"]["checker"].scores.weighted_score
            wb = tr["with"]["checker"].scores.weighted_score
            total_cost += tr["without"]["session"].cost_usd + tr["with"]["session"].cost_usd
            if wb - wa > 0.1:
                wins_b += 1
            elif wa - wb > 0.1:
                wins_a += 1
            else:
                ties += 1

        if len(all_results) > 1:
            print()
            print(f"  {'=' * 72}")
            print(f"  SUMMARY  ({len(all_results)} tasks)  |  Baseline: {wins_a}  Reflect: {wins_b}  Tie: {ties}")
            print(f"  Total cost: ${total_cost:.4f}  |  Results: {results_dir}")
            print(f"  {'=' * 72}")
        else:
            print(f"\n  Results saved: {results_dir}")

        # Save summary
        with open(results_dir / "summary.json", "w") as f:
            json.dump({
                "wins_without": wins_a,
                "wins_with": wins_b,
                "ties": ties,
                "total_cost_usd": round(total_cost, 4),
                "tasks": [t.id for t in tasks],
            }, f, indent=2)

    return 0


def cmd_report(args):
    """Regenerate report from existing results."""
    results_dir = Path("bench/results") / args.run_id
    if not results_dir.exists():
        print(f"Run not found: {results_dir}", file=sys.stderr)
        return 1

    # Read all task result files
    tasks_dir = results_dir / "tasks"
    if not tasks_dir.exists():
        print(f"No task results found in {tasks_dir}", file=sys.stderr)
        return 1

    print(f"Results for run: {args.run_id}\n")

    for f in sorted(tasks_dir.glob("*.json")):
        with open(f) as fh:
            data = json.load(fh)
        scores = data.get("checker_scores", {})
        print(f"  {data['task_id']:20s} [{data['version']:18s}] "
              f"verdict={data['checker_verdict']:6s} "
              f"score={scores.get('weighted_score', 0):.2f} "
              f"cost=${data.get('cost_usd', 0):.4f}")

    # Print summary if available
    summary_file = results_dir / "summary.json"
    if summary_file.exists():
        with open(summary_file) as f:
            summary = json.load(f)
        print(f"\n  Summary: without={summary.get('wins_without', 0)} / "
              f"with={summary.get('wins_with', 0)} / "
              f"tie={summary.get('ties', 0)}")
        print(f"  Total cost: ${summary.get('total_cost_usd', 0):.4f}")

    return 0


def cmd_list_runs(args):
    """List available benchmark runs as a scoreboard."""
    results_dir = Path("bench/results")
    if not results_dir.exists():
        print("No benchmark runs found.")
        return 0

    runs = sorted(d for d in results_dir.iterdir() if d.is_dir())
    if not runs:
        print("No benchmark runs found.")
        return 0

    print()
    print(f"  {'Run':<28s} {'Tasks':>5s}  {'Baseline':>8s}  {'Reflect':>8s}  {'Tie':>4s}  {'Cost':>8s}  {'Mode'}")
    print(f"  {'─' * 84}")

    for run_dir in runs:
        config_file = run_dir / "run_config.json"
        summary_file = run_dir / "summary.json"

        mode = "?"
        if config_file.exists():
            try:
                with open(config_file) as f:
                    cfg = json.load(f)
                mode = cfg.get("mode", "?").replace("self-bench-", "").replace("self-bench", "loop")
            except (json.JSONDecodeError, KeyError):
                pass

        if not summary_file.exists():
            tasks_dir = run_dir / "tasks"
            n = len(list(tasks_dir.glob("*.json"))) // 2 if tasks_dir.exists() else 0
            print(f"  {run_dir.name:<28s} {n:>5d}  {'—':>8s}  {'—':>8s}  {'—':>4s}  {'—':>8s}  {mode}")
            continue

        with open(summary_file) as f:
            s = json.load(f)

        # Handle both old and new summary formats
        if "wins" in s:
            wins_b = s["wins"].get("without-reflect", 0)
            wins_r = s["wins"].get("with-reflect", 0)
            ties = s["wins"].get("tie", 0)
            n_tasks = wins_b + wins_r + ties
            cost = s.get("without-reflect", {}).get("total_cost_usd", 0) + s.get("with-reflect", {}).get("total_cost_usd", 0)
        else:
            wins_b = s.get("wins_without", 0)
            wins_r = s.get("wins_with", 0)
            ties = s.get("ties", 0)
            n_tasks = wins_b + wins_r + ties
            cost = s.get("total_cost_usd", 0)

        cost_str = f"${cost:.2f}" if cost else "—"
        print(f"  {run_dir.name:<28s} {n_tasks:>5d}  {wins_b:>8d}  {wins_r:>8d}  {ties:>4d}  {cost_str:>8s}  {mode}")

    print()
    return 0


def cmd_gen_report(args):
    """Generate BENCH.md — a readable summary of all benchmark results."""
    from .tasks.registry import load_tasks

    results_dir = Path("bench/results")
    if not results_dir.exists():
        print("No benchmark results found.", file=sys.stderr)
        return 1

    tasks_file = args.tasks
    task_defs = {}
    try:
        all_tasks = load_tasks(tasks_file)
        task_defs = {t.id: t for t in all_tasks}
    except Exception:
        pass

    # Collect all runs
    runs = sorted(d for d in results_dir.iterdir() if d.is_dir())
    if not runs:
        print("No benchmark runs found.", file=sys.stderr)
        return 1

    # --- Gather per-run, per-task data ---
    run_data = []
    for run_dir in runs:
        config_file = run_dir / "run_config.json"
        summary_file = run_dir / "summary.json"
        tasks_dir = run_dir / "tasks"

        config = {}
        if config_file.exists():
            with open(config_file) as f:
                config = json.load(f)

        mode = config.get("mode", "unknown")
        model = config.get("maker_model", config.get("model", "?"))
        run_id = run_dir.name

        # Load task-level results
        task_results = []
        if tasks_dir.exists():
            task_files = sorted(tasks_dir.glob("*.json"))
            # Group by task_id
            by_task = {}
            for tf in task_files:
                with open(tf) as f:
                    td = json.load(f)
                tid = td["task_id"]
                ver = td["version"]  # "with-reflect" or "without-reflect"
                by_task.setdefault(tid, {})[ver] = td

            for tid, versions in sorted(by_task.items()):
                w = versions.get("without-reflect", {})
                r = versions.get("with-reflect", {})
                ws_w = w.get("checker_scores", {}).get("weighted_score", 0)
                ws_r = r.get("checker_scores", {}).get("weighted_score", 0)
                delta = ws_r - ws_w
                if delta > 0.1:
                    winner = "reflect"
                elif delta < -0.1:
                    winner = "baseline"
                else:
                    winner = "tie"
                task_results.append({
                    "task_id": tid,
                    "run_id": run_id,
                    "without": w,
                    "with": r,
                    "score_without": ws_w,
                    "score_with": ws_r,
                    "delta": delta,
                    "winner": winner,
                })

        summary = {}
        if summary_file.exists():
            with open(summary_file) as f:
                summary = json.load(f)

        run_data.append({
            "run_id": run_id,
            "mode": mode,
            "model": model,
            "config": config,
            "summary": summary,
            "tasks": task_results,
        })

    # --- Generate markdown ---
    lines = []
    lines.append("# Benchmark Results")
    lines.append("")
    lines.append("Self-benchmark: real Claude Code sessions solving tasks **with** vs **without** reflect context.")
    lines.append("Each task runs in an isolated git worktree. An LLM checker scores the output.")
    lines.append("")

    # Aggregate stats
    total_wins_b, total_wins_r, total_ties = 0, 0, 0
    total_cost = 0
    all_task_results = []
    for rd in run_data:
        for tr in rd["tasks"]:
            all_task_results.append(tr)
            if tr["winner"] == "reflect":
                total_wins_r += 1
            elif tr["winner"] == "baseline":
                total_wins_b += 1
            else:
                total_ties += 1
            total_cost += tr["without"].get("cost_usd", 0) + tr["with"].get("cost_usd", 0)

    total_tasks = total_wins_b + total_wins_r + total_ties

    # Headline stats
    lines.append("## Overall")
    lines.append("")
    lines.append(f"| | Count |")
    lines.append(f"|---|---:|")
    lines.append(f"| Tasks evaluated | {total_tasks} |")
    lines.append(f"| Reflect wins | **{total_wins_r}** |")
    lines.append(f"| Baseline wins | {total_wins_b} |")
    lines.append(f"| Ties | {total_ties} |")
    lines.append(f"| Win rate | **{total_wins_r/total_tasks*100:.0f}%** |" if total_tasks else "| Win rate | — |")
    lines.append(f"| Total cost | ${total_cost:.2f} |")
    lines.append("")

    # Per-task detail table
    lines.append("## Results by Task")
    lines.append("")
    lines.append("| Task | Difficulty | Baseline | Reflect | Delta | Winner | Run |")
    lines.append("|---|---|---:|---:|---:|---|---|")

    for tr in all_task_results:
        tid = tr["task_id"]
        run_id = tr["run_id"]
        tdef = task_defs.get(tid)
        diff_str = tdef.difficulty if tdef else "?"
        delta = tr["delta"]
        delta_str = f"+{delta:.2f}" if delta > 0 else f"{delta:.2f}"
        winner_str = {
            "reflect": "**Reflect**",
            "baseline": "Baseline",
            "tie": "Tie",
        }[tr["winner"]]
        # Short run label: just the timestamp part
        run_label = run_id.replace("self-", "")
        lines.append(
            f"| {tid} | {diff_str} "
            f"| {tr['score_without']:.2f} "
            f"| {tr['score_with']:.2f} "
            f"| {delta_str} "
            f"| {winner_str} "
            f"| {run_label} |"
        )

    lines.append("")

    # Per-task detail cards
    lines.append("## Task Details")
    lines.append("")

    for tr in all_task_results:
        tid = tr["task_id"]
        run_id = tr["run_id"]
        tdef = task_defs.get(tid)
        title = tdef.title if tdef else tid
        difficulty = tdef.difficulty if tdef else "?"

        w = tr["without"]
        r = tr["with"]
        ws_w = tr["score_without"]
        ws_r = tr["score_with"]
        delta = tr["delta"]

        winner_label = {"reflect": "Reflect wins", "baseline": "Baseline wins", "tie": "Tie"}[tr["winner"]]

        run_label = run_id.replace("self-", "")
        lines.append(f"### {tid} ({run_label})")
        lines.append(f"**{title}** — {difficulty}")
        lines.append("")

        # Score breakdown
        sc_w = w.get("checker_scores", {})
        sc_r = r.get("checker_scores", {})
        lines.append(f"| Metric | Baseline | Reflect |")
        lines.append(f"|---|---:|---:|")
        lines.append(f"| **Overall** | **{ws_w:.2f}** | **{ws_r:.2f}** |")
        for key, label in [("correctness", "Correctness"), ("completeness", "Completeness"),
                           ("code_quality", "Code Quality"), ("evidence_grounding", "Awareness")]:
            lines.append(f"| {label} | {sc_w.get(key, '?')}/5 | {sc_r.get(key, '?')}/5 |")
        lines.append(f"| Verdict | {w.get('checker_verdict', '?')} | {r.get('checker_verdict', '?')} |")
        lines.append(f"| Turns | {w.get('num_turns', '?')} | {r.get('num_turns', '?')} |")
        lines.append(f"| Cost | ${w.get('cost_usd', 0):.4f} | ${r.get('cost_usd', 0):.4f} |")
        lines.append("")

        # GT coverage
        for label, d in [("Baseline", w), ("Reflect", r)]:
            hits = d.get("ground_truth_hits", [])
            misses = d.get("ground_truth_misses", [])
            total = len(hits) + len(misses)
            cov = len(hits) / total if total else 0
            lines.append(f"**GT signals ({label}):** {len(hits)}/{total} ({cov:.0%})")
            if hits:
                for h in hits:
                    short = h.split(" — ")[0] if " — " in h else h
                    if len(short) > 80:
                        short = short[:77] + "..."
                    lines.append(f"- {short}")
            if misses:
                for m in misses:
                    short = m.split(" — ")[0] if " — " in m else m
                    if len(short) > 80:
                        short = short[:77] + "..."
                    lines.append(f"- ~~{short}~~")
            lines.append("")

        # Rationale
        for label, d in [("Baseline", w), ("Reflect", r)]:
            rat = d.get("checker_rationale", "")
            if rat:
                lines.append(f"> **{label}:** {rat}")
                lines.append("")

        lines.append(f"**Result: {winner_label}** (delta: {delta:+.2f})")
        lines.append("")
        lines.append("---")
        lines.append("")

    # Run log
    lines.append("## Run History")
    lines.append("")
    lines.append("| Run | Mode | Model | Tasks | Cost |")
    lines.append("|---|---|---|---:|---:|")
    for rd in run_data:
        n = len(rd["tasks"])
        cost = sum(t["without"].get("cost_usd", 0) + t["with"].get("cost_usd", 0) for t in rd["tasks"])
        lines.append(f"| {rd['run_id']} | {rd['mode']} | {rd['model']} | {n} | ${cost:.2f} |")
    lines.append("")

    # Footer
    lines.append("---")
    lines.append(f"*Generated from `python3 -m bench gen-report` — {len(run_data)} runs, {total_tasks} task evaluations.*")
    lines.append("")

    # Write
    out_path = Path(args.output)
    with open(out_path, "w") as f:
        f.write("\n".join(lines))

    print(f"Wrote {out_path} ({len(all_task_results)} tasks across {len(run_data)} runs)")
    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="bench",
        description="Benchmark reflect impact via real Claude Code sessions in sandboxed worktrees",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # self-bench (the main command now)
    p_self = sub.add_parser("self-bench", help="Run with-reflect vs without-reflect in real sandboxed sessions")
    p_self.add_argument("--repo", default=None, help="Path to repo (default: this repo)")
    p_self.add_argument("--tasks", default="bench/tasks/self_tasks.json", help="Path to self-benchmark tasks JSON")
    p_self.add_argument("--model", default="claude-sonnet-4-6", help="Claude model for sessions and checker")
    p_self.add_argument("--task", default=None, help="Run a specific task by ID (or partial match)")
    p_self.add_argument("--quick", action="store_true", help="Quick mode: 1 task only")
    p_self.add_argument("--max-budget", type=float, default=0.50, help="Max USD per session (default: $0.50)")
    p_self.add_argument("--dry-run", action="store_true", help="Show plan without running sessions")
    p_self.set_defaults(func=cmd_self_bench)

    # report
    p_report = sub.add_parser("report", help="View results from a previous run")
    p_report.add_argument("--run-id", required=True, help="Run ID to view")
    p_report.set_defaults(func=cmd_report)

    # list-runs
    p_list = sub.add_parser("list-runs", help="List available benchmark runs")
    p_list.set_defaults(func=cmd_list_runs)

    # gen-report
    p_gen = sub.add_parser("gen-report", help="Generate BENCH.md from all results")
    p_gen.add_argument("--output", default="BENCH.md", help="Output file (default: BENCH.md)")
    p_gen.add_argument("--tasks", default="bench/tasks/self_tasks.json", help="Task definitions for metadata")
    p_gen.set_defaults(func=cmd_gen_report)

    args = parser.parse_args()
    raise SystemExit(args.func(args) or 0)
