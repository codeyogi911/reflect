"""reflect status — show available evidence sources."""

import json
import os
import sys
from pathlib import Path
from .aggregates import token_window_stats
from .sources import has_entire, has_git, run


def cmd_status(args):
    """Show what evidence sources are available and their state."""
    reflect_dir = Path(".reflect")

    if not reflect_dir.exists():
        print("No .reflect/ directory. Run `reflect init` to get started.")
        return 1

    print("## Evidence Sources\n")

    # Entire CLI
    if has_entire():
        entire_raw = run(["entire", "status", "--no-pager"])
        entire_status = entire_raw.split("\n")[0] if entire_raw else ""
        from .sources import get_entire_checkpoints
        checkpoint_count = len(get_entire_checkpoints())
        print(f"- **Entire CLI**: available ({entire_status.strip()})")
        print(f"  Checkpoints: {checkpoint_count}")
    else:
        print("- **Entire CLI**: not installed")

    # Git
    if has_git():
        commit_count = run(["git", "rev-list", "--count", "HEAD"])
        last_commit = run(["git", "log", "-1", "--format=%h %ad %s", "--date=short"])
        print(f"- **Git**: {commit_count} commits")
        print(f"  Latest: {last_commit}")
    else:
        print("- **Git**: not a git repository")

    print()

    # Format config
    format_file = reflect_dir / "format.yaml"
    harness = reflect_dir / "harness"
    if format_file.exists():
        print(f"**Format**: {format_file}")
    elif harness.exists():
        print(f"**Mode**: legacy harness (migrate with `reflect init --migrate`)")
    else:
        print("**Format**: not configured (run `reflect init`)")

    # Context freshness
    context = reflect_dir / "context.md"
    last_run = reflect_dir / ".last_run"
    if context.exists():
        from datetime import datetime
        mtime = datetime.fromtimestamp(os.path.getmtime(context))
        print(f"**Context**: last generated {mtime.strftime('%Y-%m-%d %H:%M')}")
    else:
        print("**Context**: not yet generated (run `reflect context`)")

    if last_run.exists():
        try:
            state = json.loads(last_run.read_text())
            print(f"**Last run**: checkpoint={state.get('last_checkpoint', 'none')}, git={state.get('last_git_sha', 'none')}")
        except (json.JSONDecodeError, OSError):
            pass

    # Token analytics from recent sessions
    if has_entire():
        _show_token_analytics()

    return 0


def _show_token_analytics(days=7, max_sessions=30):
    """Show token usage and hot areas from recent sessions."""
    stats = token_window_stats(days=days, max_sessions=max_sessions, filter_project=True)
    if not stats:
        return

    session_count = stats["sessions_in_window"]
    total_tokens = stats["total_tokens"]
    cache_pct = stats["cache_hit_pct"]
    avg_tokens = stats["avg_tokens_per_session"]

    print(f"\n## Token Usage (last {days} days)\n")
    print(f"  Sessions: {session_count}")

    if total_tokens >= 1_000_000:
        print(f"  Total: {total_tokens / 1_000_000:.1f}M tokens")
    else:
        print(f"  Total: {total_tokens / 1_000:.1f}k tokens")

    print(f"  Cache hit rate: {cache_pct}%")

    if avg_tokens >= 1_000:
        print(f"  Avg session: {avg_tokens / 1_000:.1f}k tokens")
    else:
        print(f"  Avg session: {avg_tokens} tokens")

    hot = stats["hot_areas"]
    if hot:
        print(f"\n## Hot Areas (cross-session)\n")
        for h in hot:
            print(f"  {h['path']} — {h['count']} of {session_count} sessions")


def _is_default_harness(harness_path):
    """Check if the harness is the default one."""
    try:
        content = harness_path.read_text()
        return "Default reflect harness" in content
    except OSError:
        return False
