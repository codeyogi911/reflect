#!/usr/bin/env python3
"""Default reflect harness — closed-loop context generation.

Uses Entire CLI's AI-generated summaries (entire explain --generate) to produce
rich, semantic context. Falls back to basic git log when Entire is unavailable.

Zero intermediate storage. Entire is the memory; this is the lens.
"""

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Subprocess helper
# ---------------------------------------------------------------------------

def run(cmd, timeout=30):
    """Run a command and return stdout, or empty string on failure."""
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip() if result.returncode == 0 else ""
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""

# ---------------------------------------------------------------------------
# Evidence source readers
# ---------------------------------------------------------------------------

def has_entire():
    return shutil.which("entire") is not None

def has_git():
    return bool(run(["git", "rev-parse", "--is-inside-work-tree"]))

def get_recent_commits(limit=15):
    """Get recent commit SHAs from git log."""
    raw = run(["git", "log", f"-{limit}", "--format=%H", "--no-merges"])
    if not raw:
        return []
    return raw.split("\n")

def get_checkpoint_summary(commit_sha, generate=True):
    """Get Entire's AI summary for a commit's checkpoint.

    Returns parsed dict or None if no checkpoint exists.
    If generate=True, triggers summary generation for checkpoints without one.
    """
    raw = run(
        ["entire", "explain", "--commit", commit_sha, "--no-pager"],
        timeout=15,
    )
    if not raw or "does not have an Entire-Checkpoint trailer" in raw:
        return None

    parsed = _parse_checkpoint_output(raw)

    # Generate summary if missing (--generate requires --checkpoint flag)
    if generate and parsed and parsed.get("outcome") == "(not generated)":
        cp_id = parsed.get("checkpoint_id", "")
        if cp_id:
            gen_raw = run(
                ["entire", "explain", "--checkpoint", cp_id, "--generate", "--no-pager"],
                timeout=120,
            )
            if gen_raw and "Summary generated" in gen_raw:
                # Re-read to get the generated summary
                raw = run(
                    ["entire", "explain", "--commit", commit_sha, "--no-pager"],
                    timeout=15,
                )
                if raw:
                    parsed = _parse_checkpoint_output(raw)

    return parsed

def _parse_checkpoint_output(raw):
    """Parse the structured output of `entire explain --checkpoint`."""
    result = {
        "checkpoint_id": "",
        "session_id": "",
        "created": "",
        "tokens": 0,
        "commits": [],
        "intent": "",
        "outcome": "",
        "learnings": [],
        "friction": [],
        "open_items": [],
        "files": [],
    }

    lines = raw.split("\n")
    i = 0
    current_section = None

    while i < len(lines):
        line = lines[i]

        # Header fields
        if line.startswith("Checkpoint: "):
            result["checkpoint_id"] = line.split(": ", 1)[1]
        elif line.startswith("Session: "):
            result["session_id"] = line.split(": ", 1)[1]
        elif line.startswith("Created: "):
            result["created"] = line.split(": ", 1)[1]
        elif line.startswith("Tokens: "):
            try:
                result["tokens"] = int(line.split(": ", 1)[1])
            except ValueError:
                pass
        elif line.startswith("Intent: "):
            result["intent"] = line.split(": ", 1)[1]
        elif line.startswith("Outcome: "):
            result["outcome"] = line.split(": ", 1)[1]

        # Commits section
        elif line.startswith("Commits:"):
            i += 1
            while i < len(lines) and lines[i].startswith("  "):
                commit_match = re.match(
                    r"\s+([a-f0-9]+)\s+(\S+)\s+(.*)", lines[i]
                )
                if commit_match:
                    result["commits"].append({
                        "sha": commit_match.group(1),
                        "date": commit_match.group(2),
                        "message": commit_match.group(3).strip(),
                    })
                i += 1
            continue

        # Learnings section (multi-level indented)
        elif line.startswith("Learnings:"):
            current_section = "learnings"
            i += 1
            while i < len(lines) and (lines[i].startswith("  ") or lines[i] == ""):
                stripped = lines[i].strip()
                if stripped.startswith("- "):
                    result["learnings"].append(stripped[2:])
                elif stripped.endswith(":") and not stripped.startswith("- "):
                    # Sub-category header like "Repository:", "Code:", "Workflow:"
                    pass
                i += 1
            continue

        # Friction section
        elif line.startswith("Friction:"):
            current_section = "friction"
            i += 1
            while i < len(lines) and (lines[i].startswith("  ") or lines[i] == ""):
                stripped = lines[i].strip()
                if stripped.startswith("- "):
                    result["friction"].append(stripped[2:])
                i += 1
            continue

        # Open Items section
        elif line.startswith("Open Items:"):
            current_section = "open_items"
            i += 1
            while i < len(lines) and (lines[i].startswith("  ") or lines[i] == ""):
                stripped = lines[i].strip()
                if stripped.startswith("- "):
                    result["open_items"].append(stripped[2:])
                i += 1
            continue

        # Files section
        elif line.startswith("Files:"):
            i += 1
            while i < len(lines) and lines[i].startswith("  "):
                stripped = lines[i].strip()
                if stripped.startswith("- "):
                    result["files"].append(stripped[2:])
                i += 1
            continue

        # Stop at transcript section — we don't need it
        elif line.startswith("Transcript"):
            break

        i += 1

    return result

def get_notes(notes_dir):
    """Read manual notes from .reflect/notes/."""
    notes = []
    if not notes_dir.exists():
        return notes
    for f in sorted(notes_dir.glob("*.md")):
        content = f.read_text().strip()
        if content:
            notes.append({"name": f.stem, "content": content})
    return notes

# ---------------------------------------------------------------------------
# Section builders — powered by AI summaries
# ---------------------------------------------------------------------------

def _is_easy_to_reach(learning):
    """Return True if the learning is trivially derivable from code or git.

    Easy-to-reach signals (1-2 commands away):
    - File:line references — agent can just read the file
    - Pure code-structure facts — agent can grep/glob for these
    """
    # file:line pattern like "lib/context.py:27-31:" or "reflect:12-15:"
    if re.search(r'[a-zA-Z0-9_./-]+\.\w+:\d+', learning):
        return True
    # bare-name:line like "reflect:12-15:"
    if re.match(r'^[a-zA-Z0-9_]+:\d+', learning):
        return True
    # "file.ext does Y" patterns — starts with a file path (including dotfiles)
    if re.match(r'^\.?[a-zA-Z0-9_/.-]+\.\w+[\s:]', learning):
        return True
    return False


def build_learnings(summaries, max_lines=25):
    """Build Learnings section — only non-obvious insights.

    Filters out anything an agent can derive in 1-2 commands
    (file:line references, code-structure facts).
    """
    if not summaries:
        return []
    all_learnings = []
    seen = set()
    for s in summaries:
        for learning in s.get("learnings", []):
            # Deduplicate by first 60 chars
            key = learning[:60].lower()
            if key not in seen:
                seen.add(key)
                # Skip learnings that are easy to reach from code/git
                if not _is_easy_to_reach(learning):
                    all_learnings.append(learning)

    if not all_learnings:
        return []
    lines = ["## Learnings", "<!-- Source: AI-generated session summaries — verify before acting -->"]
    for learning in all_learnings[:max_lines - 2]:
        # Trim to fit without truncating mid-sentence
        if len(learning) > 150:
            learning = learning[:147] + "..."
        lines.append(f"- {learning}")
    lines.append("")
    return lines


def build_session_history(summaries, max_lines=20):
    """Build Session History — what happened and why, not just commit messages."""
    if not summaries:
        return []
    lines = ["## Session History", "<!-- Source: AI-generated session summaries — verify before acting -->"]
    for s in summaries:
        if not s.get("intent") or s.get("outcome") == "(not generated)":
            # Fall back to commit message for sessions without summaries
            for c in s.get("commits", []):
                lines.append(f"- {c.get('date', '')}: `{c['message']}`")
            continue

        date = s.get("created", "")[:10]
        intent = s["intent"]
        if len(intent) > 100:
            intent = intent[:97] + "..."
        outcome = s.get("outcome", "")
        if len(outcome) > 120:
            outcome = outcome[:117] + "..."

        lines.append(f"- **{date}**: {intent}")
        if outcome and outcome != "(not generated)":
            lines.append(f"  Result: {outcome}")

        if len(lines) >= max_lines:
            break
    lines.append("")
    return lines


def build_friction(summaries, max_lines=10):
    """Build Friction section — gotchas and pain points to watch for."""
    all_friction = []
    seen = set()
    for s in summaries:
        for f in s.get("friction", []):
            key = f[:60].lower()
            if key not in seen:
                seen.add(key)
                all_friction.append(f)

    if not all_friction:
        return []
    lines = ["## Friction & Gotchas", "<!-- Source: AI-generated session summaries — verify before acting -->"]
    for f in all_friction[:max_lines - 2]:
        if len(f) > 150:
            f = f[:147] + "..."
        lines.append(f"- {f}")
    lines.append("")
    return lines


def build_open_items(summaries, max_lines=10):
    """Build Open Items section — unfinished work across sessions.

    Prune items whose words overlap >50% with outcomes from newer sessions.
    Summaries are ordered newest-first, so for item at index i, outcomes
    from indices 0..i-1 are "later" (more recent).
    """
    all_items = []
    seen = set()
    for idx, s in enumerate(summaries):
        # Collect outcome words from sessions newer than this one
        newer_outcome_words = set()
        for newer in summaries[:idx]:
            outcome = newer.get("outcome", "")
            if outcome and outcome != "(not generated)":
                newer_outcome_words.update(_tokenize(outcome))

        for item in s.get("open_items", []):
            key = item[:60].lower()
            if key in seen:
                continue
            seen.add(key)
            # Prune if >50% of item words appear in newer outcomes
            item_words = _tokenize(item)
            if item_words and newer_outcome_words:
                overlap = len(item_words & newer_outcome_words) / len(item_words)
                if overlap > 0.5:
                    continue
            all_items.append(item)

    if not all_items:
        return []
    lines = ["## Open Items", "<!-- Source: AI-generated session summaries — verify before acting -->"]
    for item in all_items[:max_lines - 2]:
        if len(item) > 150:
            item = item[:147] + "..."
        lines.append(f"- {item}")
    lines.append("")
    return lines


def build_hot_areas(summaries, max_lines=8):
    """Build Hot Areas from files touched across sessions."""
    file_sessions = defaultdict(int)
    total = len(summaries)
    for s in summaries:
        seen_in_session = set()
        for f in s.get("files", []):
            if f not in seen_in_session:
                file_sessions[f] += 1
                seen_in_session.add(f)

    ranked = [(f, count) for f, count in sorted(
        file_sessions.items(), key=lambda x: -x[1]
    ) if count >= 2]

    if not ranked:
        return []
    lines = ["## Hot Areas"]
    for path, count in ranked[:max_lines - 1]:
        lines.append(f"- `{path}` — touched in {count} of {total} sessions")
    lines.append("")
    return lines


def build_notes(notes_dir, max_lines=15):
    """Build Notes section from .reflect/notes/."""
    notes = get_notes(notes_dir)
    if not notes:
        return []
    lines = ["## Notes"]
    remaining = max_lines - 1
    for note in notes:
        if remaining <= 0:
            break
        lines.append(f"### {note['name']}")
        remaining -= 1
        content_lines = note["content"].split("\n")
        for cl in content_lines[:min(8, remaining)]:
            lines.append(cl)
            remaining -= 1
        if len(content_lines) > 8:
            lines.append(f"_...({len(content_lines) - 8} more lines)_")
            remaining -= 1
    lines.append("")
    return lines


STOPWORDS = frozenset(
    "a an the is are was were be been being have has had do does did will would "
    "shall should may might can could of in to for on with at by from as into "
    "through during before after above below between out off over under again "
    "further then once here there when where why how all each every both few "
    "more most other some such no nor not only own same so than too very and "
    "but or if while about against it its this that these those i me my we our "
    "you your he him his she her they them their what which who whom".split()
)


def _tokenize(text):
    """Lowercase word tokenization with stopword removal."""
    words = set(re.findall(r'[a-z][a-z0-9_]+', text.lower()))
    return words - STOPWORDS

# ---------------------------------------------------------------------------
# Freshness state
# ---------------------------------------------------------------------------

def get_last_run(reflect_dir):
    last_run = reflect_dir / ".last_run"
    if not last_run.exists():
        return None
    try:
        return json.loads(last_run.read_text())
    except (json.JSONDecodeError, OSError):
        return None

def write_last_run(reflect_dir, checkpoint_id, git_sha):
    last_run = reflect_dir / ".last_run"
    state = {
        "last_checkpoint": checkpoint_id,
        "last_git_sha": git_sha,
        "timestamp": datetime.now().isoformat(),
    }
    last_run.write_text(json.dumps(state))

# ---------------------------------------------------------------------------
# Main context generation
# ---------------------------------------------------------------------------

def _read_config(reflect_dir):
    """Read config.yaml and return dict of settings."""
    config_file = reflect_dir / "config.yaml"
    if not config_file.exists():
        return {}
    config = {}
    for line in config_file.read_text().split("\n"):
        line = line.strip()
        if line.startswith("#") or ":" not in line:
            continue
        key, val = line.split(":", 1)
        val = val.strip()
        if val.lower() in ("true", "yes"):
            val = True
        elif val.lower() in ("false", "no"):
            val = False
        config[key.strip()] = val
    return config


def generate_context(max_lines=150):
    """Generate semantic context from Entire AI summaries + git + notes."""
    reflect_dir = Path(".reflect")
    latest_checkpoint_id = None
    latest_git_sha = None

    config = _read_config(reflect_dir)
    # Generate summaries by default — users are already sending data to AI agents
    auto_generate = config.get("auto_generate", True)

    # --- Fetch evidence ---
    summaries = []
    commits = []

    if has_git():
        commits = get_recent_commits(limit=15)
        if commits:
            latest_git_sha = commits[0][:7]

    if has_entire() and commits:
        # Get AI summaries for commits that have checkpoints
        seen_checkpoints = set()
        for sha in commits:
            summary = get_checkpoint_summary(sha, generate=auto_generate)
            if summary and summary["checkpoint_id"]:
                # Deduplicate by checkpoint (multiple commits can share one)
                if summary["checkpoint_id"] not in seen_checkpoints:
                    seen_checkpoints.add(summary["checkpoint_id"])
                    summaries.append(summary)
                    if not latest_checkpoint_id:
                        latest_checkpoint_id = summary["checkpoint_id"]
            if len(summaries) >= 10:
                break

    total_sessions = len(summaries)

    # --- Assemble context with priority-based line budget ---
    sections = []

    # Header
    header_count = f"{total_sessions} sessions analyzed" if total_sessions else "no sessions"
    sections.append("# Project Context")
    sections.append(
        "<!-- GENERATED by reflect harness — do not edit, regenerate with: reflect context -->"
    )
    sections.append(f"<!-- Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | {header_count} -->")
    sections.append("")

    # Only hard-to-derive signals. Session history, hot areas, and
    # code-structure facts are all 1-2 commands away (entire explain
    # --short, git log --stat, read the file). Don't waste context.
    section_builders = [
        lambda: build_learnings(summaries),
        lambda: build_friction(summaries),
        lambda: build_open_items(summaries),
        lambda: build_notes(reflect_dir / "notes"),
    ]

    used_lines = 4  # header
    for builder in section_builders:
        section = builder()
        if section and used_lines + len(section) <= max_lines:
            sections.extend(section)
            used_lines += len(section)

    # No evidence at all
    if used_lines <= 4:
        sections.append(
            "_No evidence sources found. Install Entire CLI for session capture, "
            "or make some git commits._"
        )
        sections.append("")

    output = "\n".join(sections)

    # Update freshness state
    if reflect_dir.exists():
        write_last_run(reflect_dir, latest_checkpoint_id, latest_git_sha)

    return output


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Default reflect harness")
    parser.add_argument("--max-lines", type=int, default=150, help="Line budget for output")
    parser.add_argument("--format", choices=["md", "json"], default="md", help="Output format")
    args = parser.parse_args()

    context = generate_context(max_lines=args.max_lines)

    if args.format == "json":
        print(json.dumps({"context": context}))
    else:
        print(context)


if __name__ == "__main__":
    main()
