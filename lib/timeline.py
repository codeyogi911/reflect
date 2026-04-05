"""reflect timeline — date-grouped view of sessions and checkpoints."""

import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta

from .fmt import format_duration, format_tokens, format_time, short_id
from .sources import has_entire, get_entire_sessions, get_session_info, get_rewind_points


def cmd_timeline(args):
    """Show date-grouped timeline of sessions and checkpoints."""
    if not has_entire():
        print("reflect timeline requires Entire CLI. Install from https://entire.dev", file=sys.stderr)
        return 1

    days = getattr(args, "days", 7)
    as_json = getattr(args, "json", False)
    cutoff = datetime.now().astimezone() - timedelta(days=days)

    sessions = get_entire_sessions()
    if not sessions:
        print("No sessions found.")
        return 1

    rewind_points = get_rewind_points()
    checkpoints_by_session = defaultdict(list)
    for rp in rewind_points:
        sid = rp.get("session_id")
        if sid:
            checkpoints_by_session[sid].append(rp)

    by_date = defaultdict(list)
    for s in sessions:
        info = get_session_info(s["session_id"], filter_project=True)
        if not info:
            continue
        try:
            started = datetime.fromisoformat(info["started_at"])
            if started.tzinfo is None:
                started = started.astimezone()
            if started < cutoff:
                break
            date_key = started.strftime("%Y-%m-%d")
        except (ValueError, KeyError, TypeError):
            continue

        entry = {
            "session_id": info["session_id"],
            "agent": info.get("agent", "?"),
            "status": info.get("status", "?"),
            "started_at": info.get("started_at", ""),
            "ended_at": info.get("ended_at"),
            "turns": info.get("turns", 0),
            "tokens": info.get("tokens", {}),
            "files_touched": info.get("files_touched", []),
            "prompt": s.get("prompt_snippet", ""),
            "checkpoints": checkpoints_by_session.get(info["session_id"], []),
        }
        by_date[date_key].append(entry)

    if not by_date:
        print(f"No sessions in the last {days} days.")
        return 1

    if as_json:
        print(json.dumps(by_date, indent=2, default=str))
        return 0

    print(f"## Project Timeline (last {days} days)\n")

    for date_key in sorted(by_date.keys(), reverse=True):
        entries = by_date[date_key]
        print(f"### {date_key}")

        for e in entries:
            start_time = format_time(e["started_at"])
            end_time = ""
            if e.get("ended_at"):
                end_time = f"-{format_time(e['ended_at'])}"
                duration = format_duration(e["started_at"], e["ended_at"])
            else:
                duration = "active"

            tokens = e.get("tokens", {})
            tok_str = format_tokens(tokens.get("total", 0))
            files = e.get("files_touched", [])
            prompt = e.get("prompt", "")[:55]
            sid = short_id(e["session_id"])

            print(f"  [{sid}] {start_time}{end_time}  {e['agent']}  \"{prompt}\"")
            print(f"    {tok_str} tokens · {duration} · "
                  f"{e['turns']} turns · {len(files)} files")

            for cp in e.get("checkpoints", []):
                cp_id = short_id(cp.get("id", cp.get("checkpoint_id", "")))
                cp_msg = cp.get("message", "")[:60]
                cp_type = "task" if cp.get("is_task_checkpoint") else "cp"
                print(f"    [{cp_type}:{cp_id}] {cp_msg}")

        print()

    return 0
