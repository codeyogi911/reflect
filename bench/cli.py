"""CLI entry point for the benchmark harness."""

import argparse
import json
import sys
from pathlib import Path

from .config import BenchmarkConfig
from .tasks.registry import load_tasks


def cmd_run(args):
    """Run the benchmark."""
    config = BenchmarkConfig(
        target_repo=args.target_repo,
        v3_reflect_dir=args.v3_reflect,
        maker_model=args.model,
        checker_model=args.model,
        max_rounds=args.max_rounds,
        tasks_file=args.tasks,
        dry_run=args.dry_run,
    )

    # Load and validate tasks
    tasks = load_tasks(config.tasks_file)
    print(f"Loaded {len(tasks)} tasks from {config.tasks_file}")

    # Create results directory
    results_dir = Path("bench/results") / config.run_id
    results_dir.mkdir(parents=True, exist_ok=True)
    tasks_dir = results_dir / "tasks"
    tasks_dir.mkdir(exist_ok=True)

    # Freeze config
    with open(results_dir / "run_config.json", "w") as f:
        json.dump(config.to_dict(), f, indent=2)
    print(f"Results directory: {results_dir}")

    if config.dry_run:
        from .context.provider import V3ContextProvider, V4ContextProvider
        v3 = V3ContextProvider(config.v3_reflect_dir)
        v4 = V4ContextProvider(config.target_repo)
        print("\n--- Dry Run: Context Sizes ---")
        for task in tasks:
            v3_ctx = v3.get_context(task)
            v4_ctx = v4.get_context(task)
            print(f"  {task.id}: v3={len(v3_ctx)} chars, v4={len(v4_ctx)} chars")
        print("\nDry run complete. No API calls made.")
        return 0

    # Import here to avoid requiring anthropic for dry runs
    from .context.provider import V3ContextProvider, V4ContextProvider
    from .loop.runner import LoopRunner
    from .metrics.collector import MetricsCollector
    from .reporting.report import generate_report

    v3_provider = V3ContextProvider(config.v3_reflect_dir)
    v4_provider = V4ContextProvider(config.target_repo)
    runner = LoopRunner(config)
    collector = MetricsCollector()

    for task in tasks:
        print(f"\n{'='*60}")
        print(f"Task: {task.id} — {task.title}")
        print(f"{'='*60}")

        # Run with v3 context
        print(f"\n  [v3] Running...")
        v3_result = runner.run_task(task, v3_provider, "v3")
        collector.add(v3_result)
        with open(tasks_dir / f"{task.id}_v3.json", "w") as f:
            json.dump(v3_result.to_dict(), f, indent=2)
        print(f"  [v3] {'Converged' if v3_result.converged else 'Did not converge'} in {v3_result.num_rounds} rounds (score: {v3_result.final_score.weighted_score:.1f})")

        # Run with v4 context
        print(f"\n  [v4] Running...")
        v4_result = runner.run_task(task, v4_provider, "v4")
        collector.add(v4_result)
        with open(tasks_dir / f"{task.id}_v4.json", "w") as f:
            json.dump(v4_result.to_dict(), f, indent=2)
        print(f"  [v4] {'Converged' if v4_result.converged else 'Did not converge'} in {v4_result.num_rounds} rounds (score: {v4_result.final_score.weighted_score:.1f})")

    # Generate summary and report
    summary = collector.summary()
    with open(results_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    report = generate_report(summary, config)
    with open(results_dir / "report.md", "w") as f:
        f.write(report)

    print(f"\n{'='*60}")
    print(f"Benchmark complete. Results: {results_dir}")
    print(f"  summary.json — machine-readable metrics")
    print(f"  report.md    — human-readable comparison")
    return 0


def cmd_report(args):
    """Regenerate report from existing results."""
    from .metrics.collector import MetricsCollector
    from .reporting.report import generate_report

    results_dir = Path("bench/results") / args.run_id
    if not results_dir.exists():
        print(f"Run not found: {results_dir}", file=sys.stderr)
        return 1

    with open(results_dir / "run_config.json") as f:
        config_dict = json.load(f)
    config = BenchmarkConfig(**{k: v for k, v in config_dict.items() if k != "run_id"}, run_id=args.run_id)

    with open(results_dir / "summary.json") as f:
        summary = json.load(f)

    report = generate_report(summary, config)
    with open(results_dir / "report.md", "w") as f:
        f.write(report)
    print(report)
    return 0


def cmd_list_runs(args):
    """List available benchmark runs."""
    results_dir = Path("bench/results")
    if not results_dir.exists():
        print("No benchmark runs found.")
        return 0

    runs = sorted(results_dir.iterdir())
    if not runs:
        print("No benchmark runs found.")
        return 0

    print(f"{'Run ID':<25} {'Tasks':<8} {'Has Report'}")
    print("-" * 50)
    for run_dir in runs:
        if not run_dir.is_dir():
            continue
        tasks_dir = run_dir / "tasks"
        task_count = len(list(tasks_dir.glob("*.json"))) // 2 if tasks_dir.exists() else 0
        has_report = "yes" if (run_dir / "report.md").exists() else "no"
        print(f"{run_dir.name:<25} {task_count:<8} {has_report}")
    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="bench",
        description="Benchmark v3 vs v4 reflect context quality via maker-checker loop",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # run
    p_run = sub.add_parser("run", help="Run the benchmark")
    p_run.add_argument("--target-repo", required=True, help="Path to the target repository")
    p_run.add_argument("--v3-reflect", required=True, help="Path to v3 .reflect/ directory")
    p_run.add_argument("--tasks", default="bench/tasks/tasks.json", help="Path to tasks JSON file")
    p_run.add_argument("--model", default="claude-sonnet-4-6", help="Claude model for maker and checker")
    p_run.add_argument("--max-rounds", type=int, default=5, help="Max maker-checker iterations")
    p_run.add_argument("--dry-run", action="store_true", help="Validate config and show context sizes without API calls")
    p_run.set_defaults(func=cmd_run)

    # report
    p_report = sub.add_parser("report", help="Regenerate report from existing run")
    p_report.add_argument("--run-id", required=True, help="Run ID to regenerate report for")
    p_report.set_defaults(func=cmd_report)

    # list-runs
    p_list = sub.add_parser("list-runs", help="List available benchmark runs")
    p_list.set_defaults(func=cmd_list_runs)

    args = parser.parse_args()
    sys.exit(args.func(args) or 0)
