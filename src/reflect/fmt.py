"""Shared formatting helpers for reflect CLI output."""

from datetime import datetime


def format_duration(started_at, ended_at):
    """Compute human-readable duration from ISO timestamps."""
    try:
        start = datetime.fromisoformat(started_at)
        end = datetime.fromisoformat(ended_at)
        total_secs = int((end - start).total_seconds())
        if total_secs < 60:
            return f"{total_secs}s"
        if total_secs < 3600:
            return f"{total_secs // 60}m"
        hours = total_secs // 3600
        mins = (total_secs % 3600) // 60
        return f"{hours}h {mins}m" if mins else f"{hours}h"
    except (ValueError, TypeError):
        return "?"


def format_tokens(total):
    """Format token count with K/M suffix."""
    if total >= 1_000_000:
        return f"{total / 1_000_000:.1f}M"
    if total >= 1_000:
        return f"{total / 1_000:.1f}k"
    return str(total)


def format_time(iso_str):
    """Extract HH:MM from ISO timestamp."""
    try:
        return datetime.fromisoformat(iso_str).strftime("%H:%M")
    except (ValueError, TypeError):
        return "?"


def short_id(full_id, length=12):
    """Truncate a UUID to a short prefix for display."""
    return full_id[:length] if full_id else "?"
