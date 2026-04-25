"""reflect improve — analyze context quality, suggest format.yaml changes.

Gathers evidence about what the context produced vs what sessions actually
needed, then outputs a structured analysis the running LLM can act on.
"""

import re
import sys
from pathlib import Path

from .evidence import gather_evidence


def analyze_context_quality(context_md):
    """Find issues in the generated context.md."""
    issues = []
    lines = context_md.strip().split("\n")

    in_section = None
    for i, line in enumerate(lines):
        if line.startswith("## "):
            if in_section and i > 0 and lines[i - 1].startswith("## "):
                issues.append(
                    {
                        "type": "empty_section",
                        "line": i + 1,
                        "detail": f"Empty section: {in_section}",
                        "fix_hint": "Section has no evidence — remove it from format.yaml or investigate source",
                    }
                )
            in_section = line[3:].strip()
            continue

        # Detect truncation artifacts
        if line.startswith("- ") and line.rstrip().endswith("..."):
            issues.append(
                {
                    "type": "truncation",
                    "line": i + 1,
                    "detail": f"Truncated text in {in_section or 'unknown'} section",
                    "fix_hint": "Subagent should summarize, not truncate — check system prompt",
                }
            )

        # Detect missing citations
        if line.startswith("- ") and not re.search(
            r"\((?:checkpoint|commit|file|session)\s+\S+\)", line
        ):
            issues.append(
                {
                    "type": "missing_citation",
                    "line": i + 1,
                    "detail": f"Bullet without reference in {in_section or 'unknown'}",
                    "fix_hint": "Set citations: required in format.yaml",
                }
            )

    return issues


def analyze_evidence_gaps(evidence, context_md):
    """Find signals in evidence that didn't make it into context."""
    gaps = []

    for cp in evidence.get("checkpoints", [])[:8]:
        cp_id = cp.get("checkpoint_id", "")[:12]
        intent = cp.get("intent", "")[:80]

        # Friction that wasn't surfaced
        for f in cp.get("friction", []):
            if f[:40] not in context_md:
                gaps.append(
                    {
                        "checkpoint": cp_id,
                        "intent": intent,
                        "type": "friction_missed",
                        "detail": f[:120],
                    }
                )

        # Open items not in context
        for item in cp.get("open_items", []):
            if item[:40] not in context_md:
                gaps.append(
                    {
                        "checkpoint": cp_id,
                        "intent": intent,
                        "type": "open_item_missed",
                        "detail": item[:120],
                    }
                )

    return gaps


def cmd_improve(args):
    """Output analysis + format config for the running LLM to propose changes."""
    reflect_dir = Path(".reflect")
    context_file = reflect_dir / "context.md"
    format_file = reflect_dir / "format.yaml"

    if not reflect_dir.exists():
        print("No .reflect/ directory. Run `reflect init` first.", file=sys.stderr)
        return 1

    sections = []
    sections.append("# Context Improvement Analysis")
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
    else:
        sections.append("## No context.md found — run `reflect context` first")
        sections.append("")

    # 2. Evidence gaps
    evidence = gather_evidence(auto_generate=False)
    if evidence["checkpoints"]:
        context_text = context_md if context_file.exists() else ""
        gaps = analyze_evidence_gaps(evidence, context_text)
        sections.append("## Evidence Gaps (signals not in context)")
        if gaps:
            for gap in gaps[:15]:
                sections.append(
                    f"- **{gap['type']}** (checkpoint {gap['checkpoint']}): {gap['detail']}"
                )
        else:
            sections.append("- No obvious gaps detected")
        sections.append("")

    # 3. Current format config
    if format_file.exists():
        sections.append("## Current format.yaml")
        sections.append("```yaml")
        sections.append(format_file.read_text().strip())
        sections.append("```")
        sections.append("")
    else:
        sections.append("## No format.yaml — using defaults")
        sections.append("")

    # 4. Suggested actions
    sections.append("## Suggested Actions")
    sections.append("")
    sections.append("Based on the analysis above, consider:")
    sections.append(
        "1. **Edit .reflect/format.yaml** — add/remove/rename sections to match what your project needs"
    )
    sections.append(
        "2. **Adjust max_bullets** — increase for sections with evidence gaps, decrease for noisy ones"
    )
    sections.append(
        "3. **Add project-specific sections** — e.g., 'API Contracts', 'Performance Gotchas', 'Migration Notes'"
    )
    sections.append("4. **Re-run `reflect context`** after changes to verify improvement")

    print("\n".join(sections))
    return 0
