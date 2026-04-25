"""reflect metrics — JSON metrics and shields.io endpoint export."""

import json
import sys
from pathlib import Path

from .aggregates import token_window_stats
from .evidence import gather_evidence
from .sources import (
    get_entire_checkpoints,
    get_entire_sessions,
    has_entire,
    has_git,
    run,
)


def _count_items(evidence, field):
    """Count unique items across checkpoints for a given field."""
    seen = set()
    for cp in evidence.get("checkpoints", []):
        for item in cp.get(field, []):
            key = item[:60].lower()
            if key not in seen:
                seen.add(key)
    return len(seen)


def _format_tokens_short(n):
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def collect_metrics(generate_summaries=False):
    """Build the full metrics dict (for JSON and export)."""
    reflect_dir = Path(".reflect")
    if not reflect_dir.exists():
        return None, "No .reflect/ directory. Run `reflect init` first."

    data = {
        "checkpoints": None,
        "sessions_total": None,
        "sessions_in_window": None,
        "tokens_window_total": None,
        "cache_hit_pct": None,
        "avg_tokens_per_session": None,
        "git_commits": None,
        "learnings_surfaced": 0,
        "friction_surfaced": 0,
        "open_items_surfaced": 0,
        "window_days": 7,
    }

    if has_entire():
        data["checkpoints"] = len(get_entire_checkpoints())
        data["sessions_total"] = len(get_entire_sessions())

    if has_git():
        c = run(["git", "rev-list", "--count", "HEAD"])
        if c.isdigit():
            data["git_commits"] = int(c)

    stats = token_window_stats(days=7, max_sessions=30, filter_project=True)
    if stats:
        data["sessions_in_window"] = stats["sessions_in_window"]
        data["tokens_window_total"] = stats["total_tokens"]
        data["cache_hit_pct"] = stats["cache_hit_pct"]
        data["avg_tokens_per_session"] = stats["avg_tokens_per_session"]

    evidence = gather_evidence(max_checkpoints=10, auto_generate=generate_summaries)
    data["learnings_surfaced"] = _count_items(evidence, "learnings")
    data["friction_surfaced"] = _count_items(evidence, "friction")
    data["open_items_surfaced"] = _count_items(evidence, "open_items")

    return data, None


def _shield(label, message, color="blue"):
    return {
        "schemaVersion": 1,
        "label": label,
        "message": message,
        "color": color,
    }


def _export_shields(data, export_dir):
    export_dir = Path(export_dir)
    export_dir.mkdir(parents=True, exist_ok=True)

    def w(name, payload):
        (export_dir / name).write_text(json.dumps(payload, indent=2) + "\n")

    na = _shield("metric", "n/a", "lightgrey")

    if data.get("checkpoints") is not None:
        w("checkpoints.json", _shield("checkpoints", str(data["checkpoints"]), "blue"))
    else:
        w("checkpoints.json", na)

    if data.get("sessions_total") is not None:
        w("sessions_total.json", _shield("sessions", str(data["sessions_total"]), "blue"))
    else:
        w("sessions_total.json", na)

    if data.get("sessions_in_window") is not None:
        w(
            "sessions_window.json",
            _shield("sessions 7d", str(data["sessions_in_window"]), "blue"),
        )
    else:
        w("sessions_window.json", na)

    if data.get("tokens_window_total") is not None:
        w(
            "tokens.json",
            _shield(
                "tokens 7d",
                _format_tokens_short(data["tokens_window_total"]),
                "green",
            ),
        )
    else:
        w("tokens.json", na)

    if data.get("cache_hit_pct") is not None:
        w(
            "cache_hit.json",
            _shield("cache hit", f"{data['cache_hit_pct']}%", "green"),
        )
    else:
        w("cache_hit.json", na)

    w(
        "learnings.json",
        _shield("learnings", str(data.get("learnings_surfaced", 0)), "informational"),
    )
    w(
        "pitfalls.json",
        _shield("pitfalls", str(data.get("friction_surfaced", 0)), "orange"),
    )
    w(
        "open_threads.json",
        _shield("open threads", str(data.get("open_items_surfaced", 0)), "yellow"),
    )


def cmd_metrics(args):
    """Print metrics JSON and/or export shields endpoint files."""
    reflect_dir = Path(".reflect")
    if not reflect_dir.exists():
        print("No .reflect/ directory. Run `reflect init` first.", file=sys.stderr)
        return 1

    if getattr(args, "no_json", False) and not getattr(args, "export_dir", None):
        print(
            "Use --export DIR with --no-json, or omit --no-json for stdout JSON.", file=sys.stderr
        )
        return 1

    data, err = collect_metrics(generate_summaries=args.generate_summaries)
    if err:
        print(err, file=sys.stderr)
        return 1

    if args.export_dir:
        _export_shields(data, args.export_dir)

    if not args.no_json:
        print(json.dumps(data, indent=2))

    return 0
