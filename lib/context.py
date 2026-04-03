"""reflect context — run the harness, write context.md."""

import os
import subprocess
import sys
from pathlib import Path


def cmd_context(args):
    """Run the harness and write context.md."""
    reflect_dir = Path(".reflect")
    harness = reflect_dir / "harness"
    context_file = reflect_dir / "context.md"

    if not reflect_dir.exists():
        print("No .reflect/ directory found. Run `reflect init` first.", file=sys.stderr)
        return 1

    if not harness.exists():
        print("No harness found at .reflect/harness. Run `reflect init` to install the default.", file=sys.stderr)
        return 1

    # Determine max_lines: CLI flag > config.yaml > harness default
    max_lines = args.max_lines
    if not max_lines:
        config_file = reflect_dir / "config.yaml"
        if config_file.exists():
            import re
            match = re.search(r'^max_lines:\s*(\d+)', config_file.read_text(), re.MULTILINE)
            if match:
                max_lines = int(match.group(1))

    flags = []
    if max_lines:
        flags.extend(["--max-lines", str(max_lines)])

    # Use the harness directly if executable, otherwise fall back to Python
    harness_cmd = [str(harness)] if os.access(harness, os.X_OK) else [sys.executable, str(harness)]

    # Longer timeout: harness may generate AI summaries via Entire CLI
    try:
        result = subprocess.run(
            harness_cmd + flags,
            capture_output=True, text=True, timeout=600
        )
    except subprocess.TimeoutExpired:
        print("Harness timed out after 600 seconds.", file=sys.stderr)
        return 1

    if result.returncode != 0:
        print(f"Harness failed:\n{result.stderr}", file=sys.stderr)
        return 1

    # Write context.md
    context_file.write_text(result.stdout)
    line_count = len(result.stdout.strip().split("\n"))
    print(f"context.md updated ({line_count} lines)")
    return 0
