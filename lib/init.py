"""reflect init — one-stop setup: install deps, create .reflect/, wire qmd."""

import os
import shutil
import subprocess
import sys
from pathlib import Path


ENTIRE_INSTALL_URL = "https://entire.io/install.sh"
QMD_NPM_PACKAGE = "@tobilu/qmd"


def _qmd_collection_name():
    """Derive a unique qmd collection name from the repo directory name."""
    cwd = Path.cwd()
    return f"reflect-{cwd.name}"


def _run(cmd, timeout=30):
    """Run a command, return (success, stdout)."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode == 0, result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False, ""


def _install_qmd():
    """Install qmd if not present. Returns True if qmd is available after this call."""
    if shutil.which("qmd"):
        return True

    print("Installing qmd (knowledge base search engine)...")

    # Try npm first
    if shutil.which("npm"):
        ok, out = _run(["npm", "install", "-g", QMD_NPM_PACKAGE], timeout=120)
        if ok and shutil.which("qmd"):
            print("qmd installed via npm.")
            return True

    # Try bun
    if shutil.which("bun"):
        ok, out = _run(["bun", "install", "-g", QMD_NPM_PACKAGE], timeout=120)
        if ok and shutil.which("qmd"):
            print("qmd installed via bun.")
            return True

    # Try npx availability check (user can use npx as fallback)
    print(
        f"Could not auto-install qmd. Install manually:\n"
        f"  npm install -g {QMD_NPM_PACKAGE}\n"
        f"Then re-run: reflect init",
        file=sys.stderr,
    )
    return False


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
    """One-stop setup: install deps, create .reflect/, register qmd collection."""
    reflect_dir = Path(".reflect")
    migrate = hasattr(args, "migrate") and args.migrate

    # --- Step 1a: qmd (required) ---
    if not _install_qmd():
        return 1

    # --- Step 1b: Entire CLI ---
    has_entire = shutil.which("entire") is not None

    if not has_entire:
        installed = _install_entire()
        if installed:
            has_entire = True
        else:
            print("Continuing without Entire CLI (knowledge base will use git-only evidence).")

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

    # --- Step 2c: qmd collection (required) ---
    if wiki:
        wiki_path = str(wiki_dir.resolve())
        collection_name = _qmd_collection_name()
        ok, _ = _run(["qmd", "collection", "add", wiki_path, "--name", collection_name])
        if ok:
            _run(["qmd", "context", "add", f"qmd://{collection_name}",
                  "Project knowledge base: decisions, patterns, preferences, gotchas, and all knowledge accumulated from coding sessions"])
            print(f"qmd collection registered: {collection_name}")
        else:
            print(f"qmd: collection {collection_name} already registered")

        # Seed embeddings if pages already exist (e.g., re-init on existing wiki)
        has_pages = any(
            f.is_file() and f.suffix == ".md" and f.name not in ("index.md", "log.md")
            for d in wiki_dir.iterdir() if d.is_dir() and not d.name.startswith("_")
            for f in d.iterdir()
        )
        if has_pages:
            print("Seeding qmd embeddings for existing wiki pages...")
            _run(["qmd", "update", "-c", collection_name], timeout=60)
            _run(["qmd", "embed", "-c", collection_name], timeout=300)

    # --- Step 3: Install skill + hooks ---
    _install_skill()

    # --- Step 4: Agent wiring ---
    _wire_agents()

    # --- Summary ---
    if already_initialized:
        print(".reflect/ already initialized. Setup checked.")
    else:
        print("Initialized .reflect/ — knowledge base ready.")
        print(f"qmd collection: {_qmd_collection_name()}")
        print("Run `reflect ingest` to seed the knowledge base from session history.")
        print("Edit .reflect/format.yaml to customize knowledge categories.")
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
    """Ensure CLAUDE.md exists and .gitignore is set up."""
    # Claude Code
    claude_md = Path("CLAUDE.md")
    if not claude_md.exists():
        claude_md.write_text("# CLAUDE.md\n")
        print("Created CLAUDE.md")

    # .gitignore
    gitignore = Path(".gitignore")
    entries_needed = [".reflect/.last_run"]
    if gitignore.exists():
        content = gitignore.read_text()
        missing = [e for e in entries_needed if e not in content]
        if missing:
            print(f"Tip: Add {', '.join(missing)} to .gitignore")
    else:
        print(f"Tip: Add {', '.join(entries_needed)} to .gitignore")

    return 0
