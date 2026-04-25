"""reflect sessions — list and inspect sessions via Entire CLI."""

import json
import sys
from datetime import datetime

from .fmt import format_duration, format_tokens, short_id
from .sources import get_entire_sessions, get_session_info, has_entire


def _cache_hit_pct(tokens):
    """Compute cache-hit percentage from token breakdown."""
    total = tokens.get("total", 0)
    cache_read = tokens.get("cache_read", 0)
    if total <= 0:
        return 0
    return round(cache_read / total * 100)


def _session_record(s, info):
    """Build a structured dict for one session (used by both text and JSON)."""
    tokens = info.get("tokens", {})
    files = info.get("files_touched", [])
    duration = "active"
    if info.get("ended_at"):
        duration = format_duration(info["started_at"], info["ended_at"])

    try:
        dt = datetime.fromisoformat(info["started_at"])
        date_str = dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, KeyError):
        date_str = "?"

    return {
        "session_id": info["session_id"],
        "agent": info.get("agent", "?"),
        "status": info.get("status", "?"),
        "started_at": info.get("started_at", ""),
        "ended_at": info.get("ended_at"),
        "date": date_str,
        "duration": duration,
        "turns": info.get("turns", 0),
        "checkpoints": info.get("checkpoints", 0),
        "tokens": {
            "total": tokens.get("total", 0),
            "input": tokens.get("input", 0),
            "cache_read": tokens.get("cache_read", 0),
            "cache_write": tokens.get("cache_write", 0),
            "output": tokens.get("output", 0),
            "cache_hit_pct": _cache_hit_pct(tokens),
        },
        "files_touched": files,
        "prompt": s.get("prompt_snippet", ""),
    }


def _show_list(limit, as_json=False):
    """List recent sessions with computed fields."""
    sessions = get_entire_sessions()
    if not sessions:
        if as_json:
            print("[]")
        else:
            print("No sessions found. Is Entire CLI configured?")
        return 1

    records = []
    for s in sessions:
        if len(records) >= limit:
            break
        info = get_session_info(s["session_id"], filter_project=True)
        if not info:
            continue
        records.append(_session_record(s, info))

    if as_json:
        print(json.dumps(records, indent=2, default=str))
        return 0

    print("## Sessions\n")
    for r in records:
        status_icon = "*" if r["status"] == "active" else "-"
        sid = short_id(r["session_id"])
        prompt = r["prompt"][:60]
        print(f'{status_icon} [{sid}] {r["date"]}  {r["agent"]}  [{r["status"]}]  "{prompt}"')
        print(
            f"  Tokens: {format_tokens(r['tokens']['total'])} (cache: {r['tokens']['cache_hit_pct']}%)  "
            f"Duration: {r['duration']}  Turns: {r['turns']}  Files: {len(r['files_touched'])}"
        )
    print()
    return 0


def _show_detail(session_id, as_json=False):
    """Show full detail for a single session."""
    info = get_session_info(session_id)
    if not info:
        sessions = get_entire_sessions()
        for s in sessions:
            if s["session_id"].startswith(session_id):
                info = get_session_info(s["session_id"])
                break
    if not info:
        print(f"Session not found: {session_id}", file=sys.stderr)
        return 1

    if as_json:
        print(json.dumps(info, indent=2, default=str))
        return 0

    tokens = info.get("tokens", {})
    files = info.get("files_touched", [])

    print(f"## Session {info['session_id']}\n")
    print(f"Agent: {info.get('agent', '?')}")
    print(f"Status: {info.get('status', '?')}")

    try:
        dt = datetime.fromisoformat(info["started_at"])
        print(f"Started: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
    except (ValueError, KeyError):
        pass

    if info.get("ended_at"):
        duration = format_duration(info["started_at"], info["ended_at"])
        print(f"Duration: {duration}")

    print(f"Turns: {info.get('turns', 0)}")
    print(f"Checkpoints: {info.get('checkpoints', 0)}")

    total = tokens.get("total", 0)
    print(f"\nTokens: {format_tokens(total)} total")
    print(f"  Input: {format_tokens(tokens.get('input', 0))}")
    print(f"  Cache read: {format_tokens(tokens.get('cache_read', 0))} ({_cache_hit_pct(tokens)}%)")
    print(f"  Cache write: {format_tokens(tokens.get('cache_write', 0))}")
    print(f"  Output: {format_tokens(tokens.get('output', 0))}")

    if files:
        print(f"\nFiles touched ({len(files)}):")
        for f in files:
            print(f"  - {f}")

    prompt = info.get("last_prompt", "")
    if prompt:
        print(f"\nLast prompt: {prompt[:200]}")

    print()
    return 0


def cmd_sessions(args):
    """List or inspect sessions tracked by Entire CLI."""
    if not has_entire():
        print(
            "reflect sessions requires Entire CLI. Install from https://entire.dev", file=sys.stderr
        )
        return 1

    session_id = getattr(args, "session_id", None)
    limit = getattr(args, "limit", 15)
    as_json = getattr(args, "json", False)

    if session_id:
        return _show_detail(session_id, as_json=as_json)
    return _show_list(limit, as_json=as_json)
