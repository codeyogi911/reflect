"""Shared evidence source utilities for the reflect CLI."""

import re
import shlex
import shutil
import subprocess
from pathlib import Path


def run(cmd, timeout=30):
    """Run a command and return stdout, or empty string on failure.

    cmd can be a list (preferred) or a string (split via shlex, no shell).
    """
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
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
            checkpoints.append({
                "id": cp_id,
                "intent": intent[:200],
                "date": dates[0] if dates else "",
                "commits": commits,
            })
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


def get_checkpoint_for_commit(sha):
    """Get checkpoint data for a specific commit via entire explain --commit."""
    raw = run(["entire", "explain", "--commit", sha, "--search-all", "--no-pager"], timeout=15)
    if not raw:
        return None
    # Parse the output: first line has "Checkpoint: <id>"
    cp_id = None
    intent = ""
    commits = []
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


def get_notes(notes_dir):
    """Read manual notes from .reflect/notes/."""
    notes = []
    notes_path = Path(notes_dir)
    if not notes_path.exists():
        return notes
    for f in sorted(notes_path.glob("*.md")):
        content = f.read_text().strip()
        if content:
            notes.append({"name": f.stem, "content": content})
    return notes
