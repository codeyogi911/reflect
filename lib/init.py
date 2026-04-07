"""reflect init — one-stop setup: install Entire, enable it, create .reflect/."""

import os
import shutil
import subprocess
import sys
from pathlib import Path


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
            shutil.copy2(_template_path("format.yaml"), format_file)
            harness.rename(reflect_dir / "harness.bak")
            print("Migrated: created format.yaml, backed up harness → harness.bak")
        elif format_file.exists():
            print("Already using format.yaml — nothing to migrate.")
        return _wire_agents()

    if not already_initialized:
        reflect_dir.mkdir(exist_ok=True)

        # Copy default format.yaml from template
        format_file = reflect_dir / "format.yaml"
        if not format_file.exists():
            shutil.copy2(_template_path("format.yaml"), format_file)

        # Copy default config from template
        config = reflect_dir / "config.yaml"
        if not config.exists():
            shutil.copy2(_template_path("config.yaml"), config)

    # --- Step 2b: Wiki (always, unless --no-wiki) ---
    no_wiki = hasattr(args, 'no_wiki') and args.no_wiki
    wiki = not no_wiki
    if wiki:
        from lib.wiki import init_wiki
        fmt = None
        format_file = reflect_dir / "format.yaml"
        if format_file.exists():
            from lib.context import load_format
            fmt = load_format(reflect_dir)
        else:
            from lib.context import DEFAULT_FORMAT
            fmt = DEFAULT_FORMAT
        wiki_dir = init_wiki(reflect_dir, fmt["sections"])
        print(f"Wiki initialized: {wiki_dir}/")

    # --- Step 2c: qmd collection (if qmd available and wiki initialized) ---
    if wiki and shutil.which("qmd"):
        wiki_path = str(wiki_dir.resolve())
        ok, _ = _run(["qmd", "collection", "add", wiki_path, "--name", "reflect-wiki"])
        if ok:
            _run(["qmd", "context", "add", "qmd://reflect-wiki", "Project memory: decisions, pitfalls, patterns, open work"])
            print("qmd collection registered: reflect-wiki")
        else:
            # Collection may already exist — not an error
            print("qmd: collection reflect-wiki already registered (or qmd error)")

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


def _template_path(name):
    """Return path to a template file shipped with reflect."""
    return _reflect_repo_root() / "templates" / name


def _install_skill():
    """Copy skill/SKILL.md, hooks/, and agents/ into supported agent dirs."""
    repo_root = _reflect_repo_root()
    skill_src = repo_root / "skill" / "SKILL.md"
    hooks_src = repo_root / "hooks"
    agents_src = repo_root / "skill" / "agents"

    if not skill_src.exists():
        return  # Not running from a reflect repo checkout

    skill_dst = Path(".claude") / "skills" / "reflect"
    skill_dst.mkdir(parents=True, exist_ok=True)

    # Copy SKILL.md
    shutil.copy2(skill_src, skill_dst / "SKILL.md")

    # Copy hooks directory
    hooks_dst = skill_dst / "hooks"
    if hooks_src.is_dir():
        if hooks_dst.is_symlink():
            hooks_dst.unlink()
        elif hooks_dst.exists():
            shutil.rmtree(hooks_dst)
        shutil.copytree(hooks_src, hooks_dst)

    # Copy agents into .claude/agents/ and clean up stale ones
    if agents_src.is_dir():
        agents_dst = Path(".claude") / "agents"
        agents_dst.mkdir(parents=True, exist_ok=True)

        # Clean up known legacy agents
        for stale in ("reflect-query.md", ".reflect-agents"):
            stale_path = agents_dst / stale
            if stale_path.exists():
                stale_path.unlink()

        for agent_file in agents_src.glob("*.md"):
            shutil.copy2(agent_file, agents_dst / agent_file.name)
        print(f"Agent installed: .claude/agents/")

    print(f"Skill installed: {skill_dst}/SKILL.md")


INSTALL_URL = "https://raw.githubusercontent.com/codeyogi911/reflect/main/install.sh"


def cmd_upgrade(args):
    """Upgrade reflect CLI, templates, skill, and agents."""
    # --- Step 1: Upgrade CLI itself ---
    print("Upgrading reflect CLI...")
    result = subprocess.run(
        ["sh", "-c", f"curl -fsSL {INSTALL_URL} | bash"],
        timeout=120,
    )
    if result.returncode != 0:
        print("CLI upgrade failed. Continuing with local updates...", file=sys.stderr)
    else:
        print()

    reflect_dir = Path(".reflect")

    if not reflect_dir.exists():
        print("No .reflect/ directory found. Run `reflect init` first.", file=sys.stderr)
        return 1

    # --- Step 2: format.yaml ---
    format_file = reflect_dir / "format.yaml"
    template = _template_path("format.yaml")
    if not template.exists():
        print("Error: templates/format.yaml not found in reflect install.", file=sys.stderr)
        return 1

    new_content = template.read_text()
    old_content = format_file.read_text() if format_file.exists() else ""

    if old_content != new_content:
        # Back up existing
        if format_file.exists():
            backup = reflect_dir / "format.yaml.bak"
            shutil.copy2(format_file, backup)
            print(f"Backed up format.yaml → format.yaml.bak")
        shutil.copy2(template, format_file)
        print("Updated format.yaml to latest template.")
    else:
        print("format.yaml already up to date.")

    # --- config.yaml ---
    config_file = reflect_dir / "config.yaml"
    config_template = _template_path("config.yaml")
    if config_template.exists() and not config_file.exists():
        shutil.copy2(config_template, config_file)
        print("Added config.yaml from template.")

    # --- Step 3: skill + hooks + agents ---
    _install_skill()

    print("Upgrade complete.")
    return 0


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
