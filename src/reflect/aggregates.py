"""Shared aggregations for reflect status and reflect metrics."""

from collections import Counter
from datetime import datetime, timedelta

from .sources import get_entire_sessions, get_session_info


def token_window_stats(days=7, max_sessions=30, filter_project=True):
    """Aggregate token usage for recent sessions in the current worktree.

    Matches reflect status token analytics: project-filtered sessions, ordered
    by recency, stopped at max_sessions or when session start is before cutoff.

    Returns None if Entire returns no sessions or none fall in the window.
    Otherwise returns a dict with sessions_in_window, total_tokens,
    total_cache_read, cache_hit_pct, avg_tokens_per_session, hot_areas
    (list of {"path", "count", "sessions_in_window"}).
    """
    sessions = get_entire_sessions()
    if not sessions:
        return None

    cutoff = datetime.now().astimezone() - timedelta(days=days)
    total_tokens = 0
    total_cache_read = 0
    session_count = 0
    file_counter = Counter()

    for s in sessions[:max_sessions]:
        info = get_session_info(s["session_id"], filter_project=filter_project)
        if not info:
            continue
        try:
            started = datetime.fromisoformat(info["started_at"])
            if started.tzinfo is None:
                started = started.astimezone()
            if started < cutoff:
                break
        except (ValueError, KeyError, TypeError):
            continue

        tokens = info.get("tokens", {})
        total_tokens += tokens.get("total", 0)
        total_cache_read += tokens.get("cache_read", 0)
        session_count += 1
        for f in info.get("files_touched", []):
            file_counter[f] += 1

    if session_count == 0:
        return None

    cache_pct = round(total_cache_read / total_tokens * 100) if total_tokens > 0 else 0
    avg_tokens = total_tokens // session_count
    hot = [
        {"path": f, "count": c, "sessions_in_window": session_count}
        for f, c in file_counter.most_common(8)
        if c >= 2
    ]

    return {
        "sessions_in_window": session_count,
        "total_tokens": total_tokens,
        "total_cache_read": total_cache_read,
        "cache_hit_pct": cache_pct,
        "avg_tokens_per_session": avg_tokens,
        "hot_areas": hot,
    }
