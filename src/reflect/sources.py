"""Shared evidence source utilities for the reflect CLI."""

import json
import os
import re
import shlex
import shutil
import subprocess


def run(cmd, timeout=30):
    """Run a command and return stdout, or empty string on failure.

    cmd can be a list (preferred) or a string (split via shlex, no shell).
    """
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip() if result.returncode == 0 else ""
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def has_entire():
    return shutil.which("entire") is not None


def has_git():
    return bool(run(["git", "rev-parse", "--is-inside-work-tree"]))


def get_entire_checkpoints():
    """Parse entire explain --short --search-all into structured data."""
    raw = run(["entire", "explain", "--short", "--search-all", "--no-pager"])
    if not raw:
        return []

    checkpoints = []
    lines = raw.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        match = re.match(r'^\[([a-f0-9-]+)\]\s+(?:\[temporary\]\s+)?"(.+)"', line)
        if match:
            cp_id = match.group(1)
            intent = match.group(2).rstrip('"').replace("\\n", " ")
            commits = []
            dates = []
            i += 1
            while i < len(lines) and lines[i].startswith("  "):
                commit_match = re.match(
                    r"^\s+(\d{2}-\d{2})\s+(\d{2}:\d{2})?\s*\(([a-f0-9]+)\)\s+(.*)",
                    lines[i],
                )
                if commit_match:
                    date_str = commit_match.group(1)
                    sha = commit_match.group(3)
                    msg = commit_match.group(4).strip()
                    commits.append({"sha": sha, "message": msg})
                    dates.append(date_str)
                i += 1
            checkpoints.append(
                {
                    "id": cp_id,
                    "intent": intent[:200],
                    "date": dates[0] if dates else "",
                    "commits": commits,
                }
            )
        else:
            i += 1
    return checkpoints


def get_entire_transcript(checkpoint_id, max_lines=100):
    """Get full transcript for a checkpoint, truncated."""
    raw = run(
        ["entire", "explain", "--checkpoint", checkpoint_id, "--full", "--no-pager"], timeout=15
    )
    if not raw:
        return ""
    lines = raw.split("\n")
    return "\n".join(lines[:max_lines])


def get_entire_sessions():
    """Get all sessions from entire sessions list, parsed into structured data."""
    raw = run(["entire", "sessions", "list"], timeout=15)
    if not raw:
        return []

    sessions = []
    lines = raw.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        # Match: "Claude Code · project · session <uuid>"
        match = re.match(r"^(.+?)\s+·\s+(.+?)\s+·\s+session\s+([a-f0-9-]+)", line)
        if match:
            agent = match.group(1).strip()
            project = match.group(2).strip()
            session_id = match.group(3)
            prompt_snippet = ""
            status_line = ""
            # Next line: > "prompt..."
            if i + 1 < len(lines) and lines[i + 1].strip().startswith(">"):
                prompt_snippet = lines[i + 1].strip().lstrip('> "').rstrip('"')
                i += 1
            # Next line: status info
            if i + 1 < len(lines) and lines[i + 1].strip():
                status_line = lines[i + 1].strip()
                i += 1
            status = "active" if "active" in status_line.split("·")[0] else "ended"
            sessions.append(
                {
                    "session_id": session_id,
                    "agent": agent,
                    "project": project,
                    "status": status,
                    "status_line": status_line,
                    "prompt_snippet": prompt_snippet,
                }
            )
        i += 1
    return sessions


def get_session_info(session_id, filter_project=False):
    """Get structured session metadata via entire sessions info --json.

    If filter_project=True, returns None for sessions from other worktrees.
    """
    raw = run(["entire", "sessions", "info", session_id, "--json"], timeout=15)
    if not raw:
        return None
    try:
        info = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    if filter_project:
        wt = info.get("worktree_path", "")
        if wt and os.path.realpath(wt) != os.path.realpath(os.getcwd()):
            return None
    return info


def get_rewind_points():
    """Get rewindable checkpoints from entire rewind --list (JSON array)."""
    raw = run(["entire", "rewind", "--list"], timeout=15)
    if not raw:
        return []
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []


def get_checkpoint_for_commit(sha):
    """Get checkpoint data for a specific commit via entire explain --commit."""
    raw = run(["entire", "explain", "--commit", sha, "--search-all", "--no-pager"], timeout=15)
    if not raw:
        return None
    # Parse the output: first line has "Checkpoint: <id>"
    cp_id = None
    intent = ""
    for line in raw.split("\n"):
        if line.startswith("Checkpoint:"):
            cp_id = line.split(":", 1)[1].strip()
        elif line.startswith("Intent:"):
            intent = line.split(":", 1)[1].strip()
        elif line.startswith("Created:"):
            date = line.split(":", 1)[1].strip()[:10]
    if not cp_id:
        return None
    return {
        "id": cp_id,
        "intent": intent,
        "date": date if date else "",
        "commits": [{"sha": sha, "message": ""}],
    }


def get_git_log(count=15):
    """Get recent git commits."""
    raw = run(["git", "log", "--oneline", f"-{count}", "--format=%h %ad %s", "--date=short"])
    if not raw:
        return []
    commits = []
    for line in raw.split("\n"):
        parts = line.split(" ", 2)
        if len(parts) >= 3:
            commits.append({"sha": parts[0], "date": parts[1], "message": parts[2]})
    return commits
