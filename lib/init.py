"""reflect init — one-stop setup: install Entire, enable it, create .reflect/."""

import os
import shutil
import subprocess
import sys
from pathlib import Path


DEFAULT_FORMAT_YAML = """\
# reflect format configuration
# Sections define what the context briefing contains.
# Edit section names and purposes to customize for your project.
# The subagent fills each section from session evidence + git history.

sections:
  - name: Key Decisions & Rationale
    purpose: why things are the way they are, not what they are
    max_bullets: 8
    recency: 30d

  - name: Gotchas & Friction
    purpose: things that burned time or surprised the agent
    max_bullets: 6
    recency: 14d

  - name: Incomplete or Abandoned Work
    purpose: things that were started but not finished, or reverted — context, not instructions
    max_bullets: 5
    recency: 7d

citations: required
max_lines: 150
"""

DEFAULT_CONFIG_YAML = """\
# reflect configuration
max_lines: 150
session_start: auto
"""

ENTIRE_INSTALL_URL = "https://entire.io/install.sh"


def _run(cmd, timeout=30):
    """Run a command, return (success, stdout)."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode == 0, result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False, ""


def _install_entire():
    """Install Entire CLI via official installer. Returns True if successful."""
    print("Installing Entire CLI...")
    try:
        # Official install: curl -fsSL https://entire.io/install | sh
        result = subprocess.run(
            ["sh", "-c", f"curl -fsSL {ENTIRE_INSTALL_URL} | bash"],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0:
            print("Entire CLI installed.")
            return True
        else:
            print(f"Entire CLI install failed: {result.stderr[:200]}", file=sys.stderr)
            return False
    except (subprocess.TimeoutExpired, OSError) as e:
        print(f"Entire CLI install failed: {e}", file=sys.stderr)
        return False


def _enable_entire():
    """Enable Entire in the current repo. Returns True if successful."""
    # Check if already enabled
    ok, out = _run(["entire", "status"])
    if ok and "Enabled" in out:
        print("Entire CLI: already enabled.")
        return True

    print("Enabling Entire CLI for this repo...")
    ok, out = _run(["entire", "enable", "--agent", "claude-code"], timeout=60)
    if ok:
        print("Entire CLI: enabled for claude-code.")
        return True
    else:
        # Try without --agent flag (interactive fallback)
        print("Entire CLI: enable failed with --agent flag, trying default...", file=sys.stderr)
        ok, out = _run(["entire", "enable"], timeout=60)
        if ok:
            print("Entire CLI: enabled.")
            return True
        print("Entire CLI: could not enable. Run `entire enable` manually.", file=sys.stderr)
        return False


def cmd_init(args):
    """One-stop setup: install Entire, enable it, create .reflect/."""
    reflect_dir = Path(".reflect")
    migrate = hasattr(args, "migrate") and args.migrate

    # --- Step 1: Entire CLI ---
    has_entire = shutil.which("entire") is not None

    if not has_entire:
        installed = _install_entire()
        if installed:
            has_entire = True
        else:
            print("Continuing without Entire CLI (context will use git-only evidence).")

    if has_entire:
        _enable_entire()

    # --- Step 2: .reflect/ directory ---
    already_initialized = reflect_dir.exists() and (
        (reflect_dir / "format.yaml").exists() or (reflect_dir / "harness").exists()
    )

    if migrate:
        # Migrate from legacy harness to format.yaml
        harness = reflect_dir / "harness"
        format_file = reflect_dir / "format.yaml"
        if harness.exists() and not format_file.exists():
            format_file.write_text(DEFAULT_FORMAT_YAML)
            harness.rename(reflect_dir / "harness.bak")
            print("Migrated: created format.yaml, backed up harness → harness.bak")
        elif format_file.exists():
            print("Already using format.yaml — nothing to migrate.")
        return _wire_agents()

    if not already_initialized:
        reflect_dir.mkdir(exist_ok=True)

        # Write default format.yaml
        format_file = reflect_dir / "format.yaml"
        if not format_file.exists():
            format_file.write_text(DEFAULT_FORMAT_YAML)

        # Write default config
        config = reflect_dir / "config.yaml"
        if not config.exists():
            config.write_text(DEFAULT_CONFIG_YAML)

    # --- Step 3: Install skill + hooks ---
    _install_skill()

    # --- Step 4: Agent wiring ---
    _wire_agents()

    # --- Summary ---
    if already_initialized:
        print(".reflect/ already initialized. Setup checked.")
    else:
        print("Initialized .reflect/ with default format.")
        print("Run `reflect context` to generate your first context briefing.")
        print("Edit .reflect/format.yaml to customize sections for your project.")
    return 0


def _reflect_repo_root():
    """Find the reflect repo root (resolving symlinks from ~/.local/bin)."""
    return Path(os.path.realpath(__file__)).parent.parent


def _install_skill():
    """Copy skill/SKILL.md and hooks/ into .claude/skills/reflect/."""
    repo_root = _reflect_repo_root()
    skill_src = repo_root / "skill" / "SKILL.md"
    hooks_src = repo_root / "hooks"

    if not skill_src.exists():
        return  # Not running from a reflect repo checkout

    skill_dst = Path(".claude") / "skills" / "reflect"
    skill_dst.mkdir(parents=True, exist_ok=True)

    # Copy SKILL.md
    shutil.copy2(skill_src, skill_dst / "SKILL.md")

    # Copy hooks directory
    hooks_dst = skill_dst / "hooks"
    if hooks_src.is_dir():
        if hooks_dst.exists():
            shutil.rmtree(hooks_dst)
        shutil.copytree(hooks_src, hooks_dst)

    print(f"Skill installed: {skill_dst}/SKILL.md")


def _wire_agents():
    """Wire context.md into agent instruction files."""
    # Claude Code
    context_ref = "@.reflect/context.md"
    claude_md = Path("CLAUDE.md")
    if claude_md.exists():
        content = claude_md.read_text()
        if context_ref not in content:
            with open(claude_md, "a") as f:
                f.write(f"\n{context_ref}\n")
            print(f"Added {context_ref} reference to CLAUDE.md")
    else:
        claude_md.write_text(f"# CLAUDE.md\n\n{context_ref}\n")
        print("Created CLAUDE.md with @.reflect/context.md reference")

    # Other agents
    other_agents = [
        (".cursorrules", "Cursor", ".cursorrules"),
        (".cursor/rules", "Cursor", ".cursor/rules/reflect.md"),
        (".github/copilot-instructions.md", "Copilot", ".github/copilot-instructions.md"),
        (".windsurfrules", "Windsurf", ".windsurfrules"),
    ]
    for check_path, agent_name, target in other_agents:
        if Path(check_path).exists():
            print(f"Tip: For {agent_name}, paste the output of `reflect context` into {target}")

    # .gitignore
    gitignore = Path(".gitignore")
    if gitignore.exists():
        content = gitignore.read_text()
        if ".reflect/context.md" not in content:
            print("Tip: Add .reflect/context.md and .reflect/.last_run to .gitignore")
    else:
        print("Tip: Add .reflect/context.md and .reflect/.last_run to .gitignore")

    return 0
