"""Fixed evidence pipeline — gathers and normalizes evidence from Entire CLI + git.

This is the internal step that feeds both the subagent and deterministic fallback.
Not user-customizable — the format.yaml controls what gets rendered, not what gets gathered.
"""

import json
import re
import shutil
import subprocess
from collections import defaultdict
from pathlib import Path

from lib.sources import run, has_entire, has_git


def gather_evidence(max_checkpoints=12, auto_generate=True):
    """Gather normalized evidence from Entire CLI + git.

    Returns dict:
        checkpoints: list of parsed checkpoint dicts (with raw_text)
        git_log: list of {sha, date, message}
        latest_checkpoint_id: str or None
        latest_git_sha: str or None
        stats: {total_checkpoints, total_commits, hot_files}
    """
    result = {
        "checkpoints": [],
        "git_log": [],
        "latest_checkpoint_id": None,
        "latest_git_sha": None,
        "stats": {"total_checkpoints": 0, "total_commits": 0, "hot_files": {}},
    }

    # --- Git evidence ---
    commits = []
    if has_git():
        raw = run(["git", "log", "-20", "--format=%H", "--no-merges"])
        if raw:
            commits = raw.split("\n")
            result["latest_git_sha"] = commits[0][:7]

        # Recent log for context
        log_raw = run(["git", "log", "--oneline", "-20", "--format=%h %ad %s", "--date=short"])
        if log_raw:
            for line in log_raw.split("\n"):
                parts = line.split(" ", 2)
                if len(parts) >= 3:
                    result["git_log"].append({"sha": parts[0], "date": parts[1], "message": parts[2]})
        result["stats"]["total_commits"] = len(result["git_log"])

    # --- Entire CLI evidence ---
    if has_entire() and commits:
        seen_checkpoints = set()
        for sha in commits:
            cp = _get_checkpoint_with_raw(sha, generate=auto_generate)
            if cp and cp["checkpoint_id"]:
                if cp["checkpoint_id"] not in seen_checkpoints:
                    seen_checkpoints.add(cp["checkpoint_id"])
                    result["checkpoints"].append(cp)
                    if not result["latest_checkpoint_id"]:
                        result["latest_checkpoint_id"] = cp["checkpoint_id"]
            if len(result["checkpoints"]) >= max_checkpoints:
                break

        result["stats"]["total_checkpoints"] = len(result["checkpoints"])

        # Compute hot files (touched in 2+ checkpoints)
        file_counts = defaultdict(int)
        for cp in result["checkpoints"]:
            seen_in_cp = set()
            for f in cp.get("files", []):
                if f not in seen_in_cp:
                    file_counts[f] += 1
                    seen_in_cp.add(f)
        result["stats"]["hot_files"] = {
            f: count for f, count in sorted(file_counts.items(), key=lambda x: -x[1])
            if count >= 2
        }

    return result


def build_evidence_document(evidence):
    """Build a text document from gathered evidence for the subagent.

    Includes raw checkpoint summaries and git log with IDs for citation.
    """
    sections = []
    sections.append("# Evidence\n")

    # Checkpoint summaries (richest source)
    if evidence["checkpoints"]:
        sections.append("## Session Checkpoints\n")
        for cp in evidence["checkpoints"]:
            cp_id = cp["checkpoint_id"][:12]
            session_id = (cp.get("session_id") or "")[:12]
            sections.append(f"### Checkpoint {cp_id} (session {session_id})")
            if cp.get("raw_text"):
                sections.append(cp["raw_text"])
            else:
                # Fallback to parsed fields
                if cp.get("intent"):
                    sections.append(f"Intent: {cp['intent']}")
                if cp.get("outcome") and cp["outcome"] != "(not generated)":
                    sections.append(f"Outcome: {cp['outcome']}")
                if cp.get("learnings"):
                    sections.append("Learnings:")
                    for l in cp["learnings"]:
                        sections.append(f"  - {l}")
                if cp.get("friction"):
                    sections.append("Friction:")
                    for f in cp["friction"]:
                        sections.append(f"  - {f}")
                if cp.get("open_items"):
                    sections.append("Open Items:")
                    for o in cp["open_items"]:
                        sections.append(f"  - {o}")
                if cp.get("files"):
                    sections.append(f"Files: {', '.join(cp['files'][:10])}")
            sections.append("")

    # Git log
    if evidence["git_log"]:
        sections.append("## Recent Git History\n")
        for entry in evidence["git_log"]:
            sections.append(f"- {entry['sha']} ({entry['date']}): {entry['message']}")
        sections.append("")

    # Hot files
    hot = evidence["stats"].get("hot_files", {})
    if hot:
        sections.append("## Hot Files (touched in 2+ sessions)\n")
        total = evidence["stats"]["total_checkpoints"]
        for f, count in list(hot.items())[:10]:
            sections.append(f"- `{f}` — {count}/{total} sessions")
        sections.append("")

    return "\n".join(sections)


def truncate_evidence(text, max_chars=20000):
    """Truncate evidence document preserving head and tail."""
    if len(text) <= max_chars:
        return text
    head = int(max_chars * 0.7)
    tail = int(max_chars * 0.2)
    omitted = len(text) - head - tail
    return f"{text[:head]}\n\n... ({omitted:,} chars omitted) ...\n\n{text[-tail:]}"


# ---------------------------------------------------------------------------
# Internal: checkpoint fetching with raw text preserved
# ---------------------------------------------------------------------------

def _get_checkpoint_with_raw(commit_sha, generate=True):
    """Get checkpoint data for a commit, preserving raw text for subagent.

    Returns parsed dict with an additional 'raw_text' field containing
    the full entire explain output (minus transcript).
    """
    raw = run(
        ["entire", "explain", "--commit", commit_sha, "--no-pager"],
        timeout=15,
    )
    if not raw or "does not have an Entire-Checkpoint trailer" in raw:
        return None

    parsed = _parse_checkpoint_output(raw)

    # Generate summary if missing
    if generate and parsed and parsed.get("outcome") == "(not generated)":
        cp_id = parsed.get("checkpoint_id", "")
        if cp_id:
            gen_raw = run(
                ["entire", "explain", "--checkpoint", cp_id, "--generate", "--no-pager"],
                timeout=120,
            )
            if gen_raw and "Summary generated" in gen_raw:
                raw = run(
                    ["entire", "explain", "--commit", commit_sha, "--no-pager"],
                    timeout=15,
                )
                if raw:
                    parsed = _parse_checkpoint_output(raw)

    # Store raw text (strip transcript section — too large)
    if raw:
        transcript_idx = raw.find("\nTranscript")
        parsed["raw_text"] = raw[:transcript_idx] if transcript_idx > 0 else raw

    return parsed


def _parse_checkpoint_output(raw):
    """Parse structured output of `entire explain --checkpoint`."""
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

    while i < len(lines):
        line = lines[i]

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

        elif line.startswith("Commits:"):
            i += 1
            while i < len(lines) and lines[i].startswith("  "):
                commit_match = re.match(r"\s+([a-f0-9]+)\s+(\S+)\s+(.*)", lines[i])
                if commit_match:
                    result["commits"].append({
                        "sha": commit_match.group(1),
                        "date": commit_match.group(2),
                        "message": commit_match.group(3).strip(),
                    })
                i += 1
            continue

        elif line.startswith("Learnings:"):
            i += 1
            while i < len(lines) and (lines[i].startswith("  ") or lines[i] == ""):
                stripped = lines[i].strip()
                if stripped.startswith("- "):
                    result["learnings"].append(stripped[2:])
                i += 1
            continue

        elif line.startswith("Friction:"):
            i += 1
            while i < len(lines) and (lines[i].startswith("  ") or lines[i] == ""):
                stripped = lines[i].strip()
                if stripped.startswith("- "):
                    result["friction"].append(stripped[2:])
                i += 1
            continue

        elif line.startswith("Open Items:"):
            i += 1
            while i < len(lines) and (lines[i].startswith("  ") or lines[i] == ""):
                stripped = lines[i].strip()
                if stripped.startswith("- "):
                    result["open_items"].append(stripped[2:])
                i += 1
            continue

        elif line.startswith("Files:"):
            i += 1
            while i < len(lines) and lines[i].startswith("  "):
                stripped = lines[i].strip()
                if stripped.startswith("- "):
                    result["files"].append(stripped[2:])
                i += 1
            continue

        elif line.startswith("Transcript"):
            break

        i += 1

    return result
