"""reflect status — show available evidence sources."""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

from .aggregates import token_window_stats
from .fmt import format_tokens
from .sources import has_entire, has_git, run


def _collect_status():
    """Gather all status data into a structured dict."""
    reflect_dir = Path(".reflect")
    if not reflect_dir.exists():
        return None, "No .reflect/ directory. Run `reflect init` to get started."

    data = {
        "entire": None,
        "git": None,
        "format": None,
        "context": None,
        "last_run": None,
        "token_usage": None,
    }

    if has_entire():
        entire_raw = run(["entire", "status", "--no-pager"])
        entire_status = entire_raw.split("\n")[0].strip() if entire_raw else ""
        from .sources import get_entire_checkpoints
        checkpoint_count = len(get_entire_checkpoints())
        data["entire"] = {
            "available": True,
            "status": entire_status,
            "checkpoints": checkpoint_count,
        }
    else:
        data["entire"] = {"available": False}

    if has_git():
        commit_count = run(["git", "rev-list", "--count", "HEAD"])
        last_commit = run(["git", "log", "-1", "--format=%h %ad %s", "--date=short"])
        data["git"] = {
            "available": True,
            "commits": int(commit_count) if commit_count.isdigit() else 0,
            "latest": last_commit,
        }
    else:
        data["git"] = {"available": False}

    format_file = reflect_dir / "format.yaml"
    harness = reflect_dir / "harness"
    if format_file.exists():
        data["format"] = {"type": "format.yaml", "path": str(format_file)}
    elif harness.exists():
        data["format"] = {"type": "legacy_harness", "path": str(harness)}
    else:
        data["format"] = {"type": "none"}

    context = reflect_dir / "context.md"
    if context.exists():
        mtime = datetime.fromtimestamp(os.path.getmtime(context))
        data["context"] = {
            "exists": True,
            "last_generated": mtime.isoformat(),
        }
    else:
        data["context"] = {"exists": False}

    last_run = reflect_dir / ".last_run"
    if last_run.exists():
        try:
            data["last_run"] = json.loads(last_run.read_text())
        except (json.JSONDecodeError, OSError):
            pass

    if has_entire():
        stats = token_window_stats(days=7, max_sessions=30, filter_project=True)
        if stats:
            data["token_usage"] = stats

    return data, None


def cmd_status(args):
    """Show what evidence sources are available and their state."""
    as_json = getattr(args, "json", False)
    data, err = _collect_status()

    if err:
        print(err, file=sys.stderr)
        return 1

    if as_json:
        print(json.dumps(data, indent=2, default=str))
        return 0

    print("## Evidence Sources\n")

    ent = data["entire"]
    if ent["available"]:
        status_detail = f" ({ent['status']})" if ent["status"] else ""
        print(f"- **Entire CLI**: available{status_detail}")
        print(f"  Checkpoints: {ent['checkpoints']}")
    else:
        print("- **Entire CLI**: not installed")

    git = data["git"]
    if git["available"]:
        print(f"- **Git**: {git['commits']} commits")
        print(f"  Latest: {git['latest']}")
    else:
        print("- **Git**: not a git repository")

    print()

    fmt = data["format"]
    if fmt["type"] == "format.yaml":
        print(f"**Format**: {fmt['path']}")
    elif fmt["type"] == "legacy_harness":
        print("**Mode**: legacy harness (migrate with `reflect init --migrate`)")
    else:
        print("**Format**: not configured (run `reflect init`)")

    ctx = data["context"]
    if ctx["exists"]:
        try:
            dt = datetime.fromisoformat(ctx["last_generated"])
            print(f"**Context**: last generated {dt.strftime('%Y-%m-%d %H:%M')}")
        except (ValueError, TypeError):
            print("**Context**: generated (unknown time)")
    else:
        print("**Context**: not yet generated (run `reflect context`)")

    lr = data.get("last_run")
    if lr:
        print(f"**Last run**: checkpoint={lr.get('last_checkpoint', 'none')}, git={lr.get('last_git_sha', 'none')}")

    stats = data.get("token_usage")
    if stats:
        _show_token_analytics(stats)

    return 0


def _show_token_analytics(stats):
    """Show token usage and hot areas from collected stats."""
    session_count = stats["sessions_in_window"]
    total_tokens = stats["total_tokens"]
    cache_pct = stats["cache_hit_pct"]
    avg_tokens = stats["avg_tokens_per_session"]

    print(f"\n## Token Usage (last 7 days)\n")
    print(f"  Sessions: {session_count}")
    print(f"  Total: {format_tokens(total_tokens)} tokens")
    print(f"  Cache hit rate: {cache_pct}%")
    print(f"  Avg session: {format_tokens(avg_tokens)} tokens")

    hot = stats.get("hot_areas", [])
    if hot:
        print(f"\n## Hot Areas (cross-session)\n")
        for h in hot:
            print(f"  {h['path']} — {h['count']} of {session_count} sessions")
