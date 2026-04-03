"""reflect init — create .reflect/ with default harness."""

import shutil
import sys
from pathlib import Path


def cmd_init(args):
    """Initialize .reflect/ directory with default harness and config."""
    reflect_dir = Path(".reflect")

    already_initialized = reflect_dir.exists() and (reflect_dir / "harness").exists()

    if not already_initialized:
        reflect_dir.mkdir(exist_ok=True)
        (reflect_dir / "notes").mkdir(exist_ok=True)

        # Copy default harness
        harness_src = Path(__file__).parent.parent / "harness" / "default.py"
        harness_dst = reflect_dir / "harness"
        if harness_src.exists():
            shutil.copy2(harness_src, harness_dst)
            harness_dst.chmod(0o755)
        else:
            print(f"Warning: default harness not found at {harness_src}", file=sys.stderr)

        # Write default config
        config = reflect_dir / "config.yaml"
        if not config.exists():
            config.write_text(
                "# reflect configuration\n"
                "max_lines: 150\n"
                "session_start: auto\n"
            )

    # Auto-wire @.reflect/context.md into Claude Code's instruction file
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

    # Detect other agent instruction files and print guidance
    other_agents = [
        (".cursorrules", "Cursor", ".cursorrules"),
        (".cursor/rules", "Cursor", ".cursor/rules/reflect.md"),
        (".github/copilot-instructions.md", "Copilot", ".github/copilot-instructions.md"),
        (".windsurfrules", "Windsurf", ".windsurfrules"),
    ]
    for check_path, agent_name, target in other_agents:
        if Path(check_path).exists():
            print(f"Tip: For {agent_name}, paste the output of `reflect context` into {target}")

    # Suggest .gitignore
    gitignore = Path(".gitignore")
    if gitignore.exists():
        content = gitignore.read_text()
        if ".reflect/context.md" not in content:
            print("Tip: Add .reflect/context.md and .reflect/.last_run to .gitignore")
    else:
        print("Tip: Add .reflect/context.md and .reflect/.last_run to .gitignore")

    if already_initialized:
        print(".reflect/ already initialized. Agent wiring checked.")
    else:
        print("Initialized .reflect/ with default harness.")
        print("Run `reflect context` to generate your first context briefing.")
    return 0
