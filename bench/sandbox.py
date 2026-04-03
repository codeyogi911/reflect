"""Sandbox — run real Claude Code sessions in isolated git worktrees.

Each benchmark run gets its own worktree so the agent can read files,
write code, and run commands without affecting the main repo. After the
session, we capture the git diff as the real output.
"""

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class SessionResult:
    """Output from a real Claude Code session."""
    diff: str  # git diff of what the agent changed
    transcript: str  # full session output (JSON)
    cost_usd: float
    input_tokens: int
    output_tokens: int
    num_turns: int
    is_error: bool = False
    error_message: str = ""
    worktree_path: str = ""


def create_worktree(repo_path: str, name: str) -> str:
    """Create an isolated git worktree for a benchmark run.

    Returns the path to the worktree directory.
    """
    # Create worktree in a temp-adjacent location
    worktree_dir = os.path.join(
        tempfile.gettempdir(), "reflect-bench", name
    )

    # Clean up if exists from a previous failed run
    if os.path.exists(worktree_dir):
        cleanup_worktree(repo_path, worktree_dir)

    os.makedirs(os.path.dirname(worktree_dir), exist_ok=True)

    # Create a detached worktree from HEAD
    branch_name = f"bench-{name}"
    result = subprocess.run(
        ["git", "worktree", "add", "-b", branch_name, worktree_dir, "HEAD"],
        capture_output=True, text=True, cwd=repo_path,
    )
    if result.returncode != 0:
        # Branch might already exist — try without -b
        result = subprocess.run(
            ["git", "worktree", "add", "--detach", worktree_dir, "HEAD"],
            capture_output=True, text=True, cwd=repo_path,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Failed to create worktree: {result.stderr}")

    return worktree_dir


def cleanup_worktree(repo_path: str, worktree_path: str):
    """Remove a git worktree and its branch."""
    # Remove the worktree
    subprocess.run(
        ["git", "worktree", "remove", "--force", worktree_path],
        capture_output=True, text=True, cwd=repo_path,
    )
    # Prune any stale worktree refs
    subprocess.run(
        ["git", "worktree", "prune"],
        capture_output=True, text=True, cwd=repo_path,
    )
    # Clean up the branch if we created one
    name = os.path.basename(worktree_path)
    branch_name = f"bench-{name}"
    subprocess.run(
        ["git", "branch", "-D", branch_name],
        capture_output=True, text=True, cwd=repo_path,
    )
    # Belt and suspenders — remove the directory if still there
    if os.path.exists(worktree_path):
        shutil.rmtree(worktree_path, ignore_errors=True)


def setup_worktree_without_reflect(worktree_path: str):
    """Strip reflect from a worktree — simulates not having reflect installed.

    - Removes .reflect/ directory
    - Removes .claude/skills/reflect/ (project Claude Code skill)
    - Removes skill/ directory (dev skill source)
    - Strips reflect pointers from CLAUDE.md
    """
    # Remove .reflect/ directory
    reflect_dir = os.path.join(worktree_path, ".reflect")
    if os.path.exists(reflect_dir):
        shutil.rmtree(reflect_dir)

    # Remove project-level Claude skill
    project_skill = os.path.join(worktree_path, ".claude", "skills", "reflect")
    if os.path.exists(project_skill):
        shutil.rmtree(project_skill)

    # Dev skill source
    skill_dir = os.path.join(worktree_path, "skill")
    if os.path.exists(skill_dir):
        shutil.rmtree(skill_dir)

    # Strip reflect references from CLAUDE.md
    claude_md = os.path.join(worktree_path, "CLAUDE.md")
    if os.path.exists(claude_md):
        with open(claude_md) as f:
            content = f.read()
        lines = [
            ln for ln in content.splitlines()
            if "@.reflect/context.md" not in ln
            and ".claude/skills/reflect" not in ln
            and "reflect skill" not in ln.lower()
        ]
        with open(claude_md, "w") as f:
            f.write("\n".join(lines))


def setup_worktree_with_reflect(worktree_path: str):
    """Ensure reflect is fully available in the worktree.

    - Regenerate context.md so it's fresh
    - CLAUDE.md and .claude/skills/reflect/ remain intact
    """
    reflect_script = os.path.join(worktree_path, "reflect")
    if os.path.exists(reflect_script):
        result = subprocess.run(
            ["python3", reflect_script, "context"],
            capture_output=True, text=True, cwd=worktree_path, timeout=30,
        )
        if result.returncode != 0:
            print(f"    [warn] reflect context failed: {result.stderr[:200]}")


def run_session(
    worktree_path: str,
    prompt: str,
    model: str = "claude-sonnet-4-6",
    max_budget_usd: float = 0.50,
    system_prompt: Optional[str] = None,
    with_reflect: bool = False,
) -> SessionResult:
    """Run a real Claude Code session in a worktree.

    The agent gets full tool access (Read, Edit, Write, Bash, Glob, Grep)
    and can actually modify code. We capture the git diff afterward.
    """
    cmd = [
        "claude", "-p",
        "--model", model,
        "--output-format", "json",
        "--permission-mode", "acceptEdits",
        "--max-budget-usd", str(max_budget_usd),
        "--allowedTools", "Read,Edit,Write,Bash,Glob,Grep",
    ]

    if system_prompt:
        cmd.extend(["--append-system-prompt", system_prompt])

    try:
        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=600,  # 10 min max per session
            cwd=worktree_path,
        )
    except subprocess.TimeoutExpired:
        return SessionResult(
            diff="", transcript="", cost_usd=0, input_tokens=0,
            output_tokens=0, num_turns=0, is_error=True,
            error_message="Session timed out after 600s",
            worktree_path=worktree_path,
        )

    # Parse the JSON output
    try:
        data = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError):
        return SessionResult(
            diff="", transcript=result.stdout or "",
            cost_usd=0, input_tokens=0, output_tokens=0, num_turns=0,
            is_error=True,
            error_message=f"CLI error (rc={result.returncode}): {result.stderr[:500]}",
            worktree_path=worktree_path,
        )

    # Extract metrics — even from errored sessions (budget exceeded still has usage)
    cost = data.get("total_cost_usd", 0.0)
    input_tokens = 0
    output_tokens = 0
    usage_data = data.get("modelUsage", data.get("usage", {}))
    if isinstance(usage_data, dict):
        # Handle both top-level usage and per-model usage formats
        if any(isinstance(v, dict) for v in usage_data.values()):
            for mu in usage_data.values():
                if isinstance(mu, dict):
                    input_tokens += mu.get("inputTokens", 0) + mu.get("cacheReadInputTokens", 0) + mu.get("cache_read_input_tokens", 0)
                    output_tokens += mu.get("outputTokens", 0) + mu.get("output_tokens", 0)
        else:
            input_tokens = usage_data.get("input_tokens", 0) + usage_data.get("cache_read_input_tokens", 0)
            output_tokens = usage_data.get("output_tokens", 0)

    num_turns = data.get("num_turns", 0)
    session_text = data.get("result", "")

    # ALWAYS capture the git diff — even on budget-exceeded, partial work is valuable
    diff = _get_diff(worktree_path)

    is_error = data.get("is_error", False)
    error_msg = ""
    if is_error:
        subtype = data.get("subtype", "")
        error_msg = f"{subtype}: {session_text[:200]}" if subtype else str(session_text)[:200]

    return SessionResult(
        diff=diff,
        transcript=session_text if not is_error else json.dumps(data, indent=2),
        cost_usd=cost,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        num_turns=num_turns,
        is_error=is_error,
        error_message=error_msg,
        worktree_path=worktree_path,
    )


def _get_diff(worktree_path: str) -> str:
    """Get the full diff of all changes in the worktree."""
    # Stage everything first so we capture new files too
    subprocess.run(
        ["git", "add", "-A"],
        capture_output=True, text=True, cwd=worktree_path,
    )
    result = subprocess.run(
        ["git", "diff", "--cached", "--stat"],
        capture_output=True, text=True, cwd=worktree_path,
    )
    stat = result.stdout.strip()

    result = subprocess.run(
        ["git", "diff", "--cached"],
        capture_output=True, text=True, cwd=worktree_path,
    )
    full_diff = result.stdout.strip()

    if stat and full_diff:
        return f"# Diff Summary\n{stat}\n\n# Full Diff\n{full_diff}"
    elif full_diff:
        return full_diff
    else:
        return "(no changes)"
