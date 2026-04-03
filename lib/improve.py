"""reflect improve — analyze harness effectiveness, propose changes.

Gathers evidence about what the harness produced vs what sessions actually
needed, then outputs a structured analysis the running LLM can act on.

reflect does not call LLMs — it prepares the evidence. The agent reasons.
"""

import os
import re
import sys
from pathlib import Path

# Import from the harness to reuse evidence readers
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
from harness.default import (
    get_checkpoint_summary,
    get_recent_commits,
    has_entire,
    has_git,
    run,
)


def analyze_context_quality(context_md):
    """Find issues in the generated context.md."""
    issues = []
    lines = context_md.strip().split("\n")

    in_section = None
    for i, line in enumerate(lines):
        # Track current section and detect empty sections
        if line.startswith("## "):
            # Check if previous section was empty (two headers in a row)
            if in_section and i > 0 and lines[i - 1].startswith("## "):
                issues.append({
                    "type": "empty_section",
                    "line": i + 1,
                    "detail": f"Empty section: {in_section}",
                    "fix_hint": "Section has no content — either remove it or investigate why",
                })
            in_section = line[3:].strip()
            continue

        # Detect truncation artifacts in any bullet
        if line.startswith("- ") and line.rstrip().endswith("..."):
            issues.append({
                "type": "truncation",
                "line": i + 1,
                "detail": f"Truncated text in {in_section or 'unknown'} section — reader can't act on it",
                "fix_hint": "Summarize rather than truncate, or skip entries that don't fit",
            })

        # Detect sessions without AI summaries (commit-message fallback: "- DATE: `commit msg`")
        if in_section == "Session History" and line.startswith("- ") and ": `" in line and not line.startswith("- **"):
            issues.append({
                "type": "no_summary",
                "line": i + 1,
                "detail": "Session fell back to commit message — no AI summary available",
                "fix_hint": "Run `entire explain -c <checkpoint_id> --generate` or set `auto_generate: true` in .reflect/config.yaml",
            })

    return issues


def analyze_summary_gaps(summaries):
    """Find things sessions needed that the harness didn't surface."""
    gaps = []

    for s in summaries[:5]:
        cp_id = s.get("checkpoint_id", "")[:12]
        intent = s.get("intent", "")[:80]

        # Sessions without generated summaries are themselves a gap
        if s.get("outcome") == "(not generated)":
            gaps.append({
                "session": cp_id,
                "intent": intent,
                "type": "no_summary",
                "detail": f"No AI summary generated — run `entire explain -c {cp_id} --generate`",
                "examples": [],
            })
            continue

        # Friction items suggest the harness could pre-surface warnings
        for f in s.get("friction", []):
            gaps.append({
                "session": cp_id,
                "intent": intent,
                "type": "friction_not_surfaced",
                "detail": f"Friction encountered: {f[:100]}",
                "examples": [],
            })

    return gaps


def _similarity(a, b):
    """Jaccard word similarity."""
    wa = set(a.split())
    wb = set(b.split())
    if not wa or not wb:
        return 0
    return len(wa & wb) / len(wa | wb)


def cmd_improve(args):
    """Output analysis + harness source for the running LLM to propose changes."""
    reflect_dir = Path(".reflect")
    harness_path = reflect_dir / "harness"
    context_file = reflect_dir / "context.md"

    if not reflect_dir.exists():
        print("No .reflect/ directory. Run `reflect init` first.", file=sys.stderr)
        return 1

    # --- Gather evidence ---
    sections = []
    sections.append("# Harness Improvement Analysis")
    sections.append("")

    # 1. Current context quality
    if context_file.exists():
        context_md = context_file.read_text()
        issues = analyze_context_quality(context_md)
        sections.append("## Context Quality Issues")
        if issues:
            for issue in issues:
                sections.append(f"- **{issue['type']}** (line {issue['line']}): {issue['detail']}")
                sections.append(f"  Fix: {issue['fix_hint']}")
        else:
            sections.append("- No issues detected in current context.md")
        sections.append("")

        sections.append("## Current context.md")
        sections.append("```markdown")
        sections.append(context_md.strip())
        sections.append("```")
        sections.append("")

    # 2. Summary gaps
    if has_entire() and has_git():
        commits = get_recent_commits(limit=10)
        summaries = []
        seen = set()
        for sha in commits:
            s = get_checkpoint_summary(sha, generate=False)
            if s and s["checkpoint_id"] and s["checkpoint_id"] not in seen:
                seen.add(s["checkpoint_id"])
                summaries.append(s)
        gaps = analyze_summary_gaps(summaries)
        sections.append("## Evidence Gaps")
        if gaps:
            for gap in gaps:
                sections.append(f"- **{gap['type']}** (session {gap['session']}): {gap['detail']}")
                for ex in gap.get("examples", []):
                    sections.append(f"  - `{ex[:80]}`")
        else:
            sections.append("- No obvious gaps detected")
        sections.append("")

    # 3. Harness source (so the LLM can propose changes)
    harness_source = None
    if harness_path.exists():
        # Resolve symlink to get actual harness source
        real_path = harness_path.resolve()
        harness_source = real_path.read_text()
        sections.append(f"## Current Harness Source ({real_path})")
        sections.append("```python")
        sections.append(harness_source.strip())
        sections.append("```")
        sections.append("")

    # 4. Improvement prompt for the LLM
    sections.append("## Suggested Action")
    sections.append("")
    sections.append("Based on the issues above, propose specific edits to the harness source.")
    sections.append("Focus on changes that:")
    sections.append("1. Reduce noise (filter out non-decisions, vague keywords)")
    sections.append("2. Fill gaps (surface information the agent had to search for)")
    sections.append("3. Are minimal — change the least code for the most impact")
    sections.append("")
    sections.append("The harness is a Python script. Edit it directly.")

    print("\n".join(sections))
    return 0
