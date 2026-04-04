"""reflect context — gather evidence, synthesize via subagent, write context.md.

Pipeline: evidence (fixed) → format.yaml (user-configurable) → subagent → validate → write.
Falls back to deterministic rendering if claude CLI is unavailable.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from lib.evidence import gather_evidence, build_evidence_document, truncate_evidence


# ---------------------------------------------------------------------------
# Format config
# ---------------------------------------------------------------------------

DEFAULT_FORMAT = {
    "sections": [
        {
            "name": "Key Decisions & Rationale",
            "purpose": "why things are the way they are, not what they are",
            "max_bullets": 8,
            "recency": "30d",
        },
        {
            "name": "Gotchas & Friction",
            "purpose": "things that burned time or surprised the agent",
            "max_bullets": 6,
            "recency": "14d",
        },
        {
            "name": "Open Work",
            "purpose": "unfinished items a new session should pick up",
            "max_bullets": 5,
            "recency": "7d",
        },
        {
            "name": "Critical Pitfalls",
            "purpose": "agent mistakes, reverted work, and failed approaches — each entry is a DON'T rule backed by evidence of what went wrong",
            "max_bullets": 8,
            "recency": "90d",
            "entry_fields": ["mistake", "consequence", "rule"],
        },
    ],
    "citations": "required",
    "max_lines": 150,
}


def load_format(reflect_dir):
    """Load .reflect/format.yaml, falling back to defaults."""
    format_file = reflect_dir / "format.yaml"
    if not format_file.exists():
        return DEFAULT_FORMAT.copy()

    config = DEFAULT_FORMAT.copy()
    raw = format_file.read_text()

    # Parse YAML-lite (no PyYAML dependency)
    sections = []
    current_section = None
    in_sections = False
    in_entry_fields = False

    for line in raw.split("\n"):
        stripped = line.strip()
        if stripped.startswith("#") or not stripped:
            continue

        # Top-level keys
        if not line.startswith(" ") and not line.startswith("\t"):
            if stripped.startswith("sections:"):
                in_sections = True
                continue
            in_sections = False
            in_entry_fields = False
            if ":" in stripped:
                key, val = stripped.split(":", 1)
                val = val.strip()
                if key.strip() == "citations":
                    config["citations"] = val
                elif key.strip() == "max_lines":
                    try:
                        config["max_lines"] = int(val)
                    except ValueError:
                        pass
            continue

        # Inside sections list
        if in_sections:
            if stripped.startswith("- name:"):
                in_entry_fields = False
                if current_section:
                    sections.append(current_section)
                current_section = {
                    "name": stripped.split(":", 1)[1].strip().strip('"').strip("'"),
                    "purpose": "",
                    "max_bullets": 8,
                    "recency": "30d",
                }
            elif current_section and stripped.startswith("entry_fields:"):
                in_entry_fields = True
                current_section["entry_fields"] = []
            elif in_entry_fields and stripped.startswith("- "):
                # Strip comments from entry_fields items
                field = stripped[2:].split("#")[0].strip()
                if field:
                    current_section["entry_fields"].append(field)
            elif current_section and ":" in stripped:
                in_entry_fields = False
                key, val = stripped.split(":", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key == "purpose":
                    current_section["purpose"] = val
                elif key == "max_bullets":
                    try:
                        current_section["max_bullets"] = int(val)
                    except ValueError:
                        pass
                elif key == "recency":
                    current_section["recency"] = val

    if current_section:
        sections.append(current_section)
    if sections:
        config["sections"] = sections

    return config


# ---------------------------------------------------------------------------
# Subagent synthesis
# ---------------------------------------------------------------------------

MODEL = os.environ.get("REFLECT_MODEL", "claude-haiku-4-5-20251001")
MAX_BUDGET = os.environ.get("REFLECT_CONTEXT_BUDGET", "0.05")


def _build_system_prompt(fmt):
    """Build subagent system prompt from format config."""
    section_instructions = []
    for s in fmt["sections"]:
        block = (
            f"### {s['name']}\n"
            f"Purpose: {s['purpose']}\n"
            f"Max bullets: {s['max_bullets']}\n"
            f"Recency window: {s['recency']}"
        )
        if s.get("entry_fields"):
            fields = ", ".join(s["entry_fields"])
            block += f"\nRequired fields per entry: {fields}. Format each bullet as: **{s['entry_fields'][0]}** — <value>. {', '.join(f'**{f}**: <value>' for f in s['entry_fields'][1:])}."
        section_instructions.append(block)

    citation_rule = (
        "Every bullet MUST include at least one reference so the agent can explore further."
        if fmt.get("citations") == "required"
        else "Include references where possible."
    )

    return f"""\
You are a context distiller for AI coding agents. You receive RAW EVIDENCE \
from session transcripts and git history for a software project. Your job is \
to produce a concise context briefing that helps a NEW agent session start \
productively.

SECTIONS TO PRODUCE:

{chr(10).join(section_instructions)}

WHAT TO INCLUDE (hard-to-derive signals only):
- Design decisions and their rationale (WHY, not WHAT)
- Gotchas, failure modes, and workarounds discovered through pain
- Cross-session patterns (things that come up repeatedly)
- Unfinished work that a new session should know about
- Architectural constraints not obvious from reading the code
- **CRITICAL PITFALLS** — the most important category. Look for:
  - Revert commits (evidence section "Revert Commits" and "Pitfalls")
  - Friction items that mention failure, wrong approach, broken, reverted
  - Sequences where something was built then undone in a later checkpoint
  - Each pitfall MUST be phrased as a "don't" rule: what not to do and why

WHAT TO EXCLUDE:
- Anything derivable from reading the code (file structure, function names, imports)
- Anything derivable from git log (commit messages, who changed what when)
- Generic programming advice not specific to this project
- Vague or trivially obvious observations

REFERENCES — CRITICAL:
{citation_rule}
Use these formats at the end of each bullet:
- (checkpoint <id-prefix>) — for session checkpoint evidence
- (commit <short-sha>) — for git commit evidence
- (file <path>) — for file-based evidence

The agent consuming this has access to `entire explain --checkpoint <id>` \
and `git show <sha>` to dig deeper. Be the index, not the encyclopedia.

OUTPUT FORMAT:
- Start with: # Project Context
- Then each section as ## <Section Name>
- Plain markdown bullets, no nested lists
- Keep total output under {fmt['max_lines']} lines
- Omit sections that have no relevant evidence
- Do NOT include commentary, preamble, or meta-discussion
- Do NOT wrap output in code fences"""


def _synthesize_context(evidence_doc, fmt, verbose=False):
    """Call Claude subagent to produce context.md from evidence + format.

    Returns markdown string or None on failure.
    """
    if not shutil.which("claude"):
        if verbose:
            print("  [context] claude CLI not found, using fallback", file=sys.stderr)
        return None

    system_prompt = _build_system_prompt(fmt)
    evidence_doc = truncate_evidence(evidence_doc)

    prompt = f"Produce the context briefing from this evidence.\n\n{evidence_doc}"

    cmd = [
        "claude", "-p",
        "--model", MODEL,
        "--output-format", "json",
        "--max-turns", "1",
        "--tools", "",
        "--max-budget-usd", MAX_BUDGET,
        "--append-system-prompt", system_prompt,
    ]

    if verbose:
        print(f"  [context] calling {MODEL} (budget ${MAX_BUDGET})...", file=sys.stderr)

    try:
        result = subprocess.run(
            cmd, input=prompt, capture_output=True, text=True, timeout=120,
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        if verbose:
            print(f"  [context] failed: {e}", file=sys.stderr)
        return None

    if result.returncode != 0:
        if verbose:
            print(f"  [context] CLI exited {result.returncode}", file=sys.stderr)
        return None

    try:
        data = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError):
        if verbose:
            print("  [context] failed to parse CLI output", file=sys.stderr)
        return None

    if data.get("is_error"):
        if verbose:
            print(f"  [context] CLI error: {data.get('result', '')[:100]}", file=sys.stderr)
        return None

    raw_output = data.get("result", "")

    # Strip markdown fences if model wrapped output
    if raw_output.strip().startswith("```"):
        lines = raw_output.strip().split("\n")
        if lines[-1].strip() == "```":
            raw_output = "\n".join(lines[1:-1])
        else:
            raw_output = "\n".join(lines[1:])

    return raw_output.strip()


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _validate_output(context_md, fmt):
    """Validate subagent output. Returns (is_valid, issues)."""
    issues = []
    lines = context_md.strip().split("\n")

    # Check line budget
    if len(lines) > fmt["max_lines"] * 1.2:  # 20% grace
        issues.append(f"Over budget: {len(lines)} lines (max {fmt['max_lines']})")

    # Check citations if required
    if fmt.get("citations") == "required":
        bullet_count = 0
        uncited_count = 0
        for line in lines:
            if line.strip().startswith("- "):
                bullet_count += 1
                # Check for reference pattern
                if not re.search(r'\((?:checkpoint|commit|file|session)\s+\S+\)', line):
                    uncited_count += 1

        if bullet_count > 0 and uncited_count > bullet_count * 0.3:
            issues.append(f"{uncited_count}/{bullet_count} bullets missing citations")

    # Check sections exist
    section_names = {s["name"].lower() for s in fmt["sections"]}
    found_sections = set()
    for line in lines:
        if line.startswith("## "):
            found_sections.add(line[3:].strip().lower())

    # At least one section should be present (unless no evidence)
    if not found_sections:
        issues.append("No sections found in output")

    return len(issues) == 0, issues


def _repair_citations(context_md, evidence):
    """Best-effort repair: add checkpoint references to uncited bullets."""
    lines = context_md.split("\n")
    repaired = []

    # Build a keyword → checkpoint map from evidence
    keyword_map = {}
    for cp in evidence.get("checkpoints", []):
        cp_id = cp["checkpoint_id"][:12]
        words = set()
        for field in ["intent", "outcome"]:
            if cp.get(field):
                words.update(w.lower() for w in re.findall(r'[a-z][a-z0-9_]+', cp[field].lower()))
        for field in ["learnings", "friction", "open_items"]:
            for item in cp.get(field, []):
                words.update(w.lower() for w in re.findall(r'[a-z][a-z0-9_]+', item.lower()))
        for w in words:
            if w not in keyword_map:
                keyword_map[w] = cp_id

    for line in lines:
        if line.strip().startswith("- ") and not re.search(r'\((?:checkpoint|commit|file|session)\s+\S+\)', line):
            # Try to find a matching checkpoint
            line_words = set(re.findall(r'[a-z][a-z0-9_]+', line.lower()))
            best_cp = None
            best_overlap = 0
            for cp in evidence.get("checkpoints", []):
                cp_words = set()
                for field in ["intent", "outcome"] + [
                    item for f in ["learnings", "friction", "open_items"] for item in cp.get(f, [])
                ]:
                    if isinstance(field, str):
                        cp_words.update(w.lower() for w in re.findall(r'[a-z][a-z0-9_]+', field.lower()))
                overlap = len(line_words & cp_words)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_cp = cp["checkpoint_id"][:12]
            if best_cp and best_overlap >= 3:
                line = line.rstrip() + f" (checkpoint {best_cp})"
        repaired.append(line)

    return "\n".join(repaired)


# ---------------------------------------------------------------------------
# Deterministic fallback
# ---------------------------------------------------------------------------

def _deterministic_context(evidence, fmt):
    """Generate context without LLM — uses parsed checkpoint fields directly.

    Simpler than the old harness but follows the same format.yaml sections.
    """
    sections = []
    sections.append("# Project Context")

    checkpoints = evidence.get("checkpoints", [])
    if not checkpoints:
        sections.append("")
        sections.append("_No session evidence found. Install Entire CLI for session capture, "
                        "or make some git commits._")
        return "\n".join(sections)

    for section_def in fmt["sections"]:
        name = section_def["name"].lower()
        bullets = []

        if "decision" in name or "rationale" in name:
            # Use intent + outcome pairs as decision signals
            for cp in checkpoints:
                if cp.get("intent") and cp.get("outcome") and cp["outcome"] != "(not generated)":
                    cp_id = cp["checkpoint_id"][:12]
                    bullets.append(f"- {cp['intent'][:120]} → {cp['outcome'][:80]} (checkpoint {cp_id})")
                if len(bullets) >= section_def["max_bullets"]:
                    break

        elif "gotcha" in name or "friction" in name:
            seen = set()
            for cp in checkpoints:
                for f in cp.get("friction", []):
                    key = f[:60].lower()
                    if key not in seen:
                        seen.add(key)
                        cp_id = cp["checkpoint_id"][:12]
                        bullets.append(f"- {f} (checkpoint {cp_id})")
                if len(bullets) >= section_def["max_bullets"]:
                    break

        elif "pitfall" in name or "mistake" in name or "don't" in name:
            pitfalls = evidence.get("pitfalls", [])
            seen = set()
            for p in pitfalls:
                key = p["description"][:60].lower()
                if key not in seen:
                    seen.add(key)
                    bullets.append(f"- **{p['description']}** ({p['source_id']})")
                if len(bullets) >= section_def["max_bullets"]:
                    break

        elif "open" in name or "work" in name or "unfinished" in name or "incomplete" in name:
            seen = set()
            for cp in checkpoints:
                for item in cp.get("open_items", []):
                    key = item[:60].lower()
                    if key not in seen:
                        seen.add(key)
                        cp_id = cp["checkpoint_id"][:12]
                        bullets.append(f"- {item} (checkpoint {cp_id})")
                if len(bullets) >= section_def["max_bullets"]:
                    break

        else:
            # Generic: pull learnings
            seen = set()
            for cp in checkpoints:
                for l in cp.get("learnings", []):
                    key = l[:60].lower()
                    if key not in seen:
                        seen.add(key)
                        cp_id = cp["checkpoint_id"][:12]
                        bullets.append(f"- {l} (checkpoint {cp_id})")
                if len(bullets) >= section_def["max_bullets"]:
                    break

        if bullets:
            sections.append("")
            sections.append(f"## {section_def['name']}")
            sections.extend(bullets[:section_def["max_bullets"]])

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Freshness state
# ---------------------------------------------------------------------------

def _write_last_run(reflect_dir, checkpoint_id, git_sha):
    last_run = reflect_dir / ".last_run"
    state = {
        "last_checkpoint": checkpoint_id,
        "last_git_sha": git_sha,
        "timestamp": datetime.now().isoformat(),
    }
    last_run.write_text(json.dumps(state))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def cmd_context(args):
    """Generate context.md via evidence pipeline + subagent."""
    reflect_dir = Path(".reflect")
    context_file = reflect_dir / "context.md"

    if not reflect_dir.exists():
        print("No .reflect/ directory found. Run `reflect init` first.", file=sys.stderr)
        return 1

    # Legacy escape hatch: if .reflect/harness exists, use it
    harness = reflect_dir / "harness"
    if harness.exists():
        return _run_legacy_harness(harness, args, context_file)

    # Load format config
    fmt = load_format(reflect_dir)

    # Override max_lines from CLI
    if hasattr(args, "max_lines") and args.max_lines:
        fmt["max_lines"] = args.max_lines

    # Read config for auto_generate setting
    auto_generate = True
    config_file = reflect_dir / "config.yaml"
    if config_file.exists():
        for line in config_file.read_text().split("\n"):
            if line.strip().startswith("auto_generate:"):
                val = line.split(":", 1)[1].strip().lower()
                auto_generate = val in ("true", "yes")

    verbose = hasattr(args, "verbose") and args.verbose

    # --- Pipeline ---
    print("Gathering evidence...", file=sys.stderr)
    evidence = gather_evidence(auto_generate=auto_generate)

    total = evidence["stats"]["total_checkpoints"]
    print(f"Found {total} checkpoints, {evidence['stats']['total_commits']} commits", file=sys.stderr)

    # Build evidence document for subagent
    evidence_doc = build_evidence_document(evidence)

    # Try subagent synthesis
    context_md = _synthesize_context(evidence_doc, fmt, verbose=verbose)

    if context_md:
        # Validate
        is_valid, issues = _validate_output(context_md, fmt)
        if not is_valid:
            if verbose:
                for issue in issues:
                    print(f"  [validate] {issue}", file=sys.stderr)
            # Try to repair citations
            if any("citations" in i for i in issues):
                context_md = _repair_citations(context_md, evidence)
                is_valid, issues = _validate_output(context_md, fmt)

        # Add header comment
        header = (
            "<!-- GENERATED by reflect — do not edit, regenerate with: reflect context -->\n"
            f"<!-- Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | "
            f"{total} sessions analyzed -->\n"
        )
        # Insert header after # Project Context if present
        if context_md.startswith("# Project Context"):
            first_newline = context_md.index("\n")
            context_md = context_md[:first_newline + 1] + header + context_md[first_newline + 1:]
        else:
            context_md = "# Project Context\n" + header + context_md

        source = "subagent"
    else:
        # Deterministic fallback
        print("Using deterministic fallback...", file=sys.stderr)
        context_md = _deterministic_context(evidence, fmt)

        header = (
            "<!-- GENERATED by reflect (deterministic) — do not edit, regenerate with: reflect context -->\n"
            f"<!-- Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | "
            f"{total} sessions analyzed -->\n"
        )
        if context_md.startswith("# Project Context"):
            first_newline = context_md.index("\n")
            context_md = context_md[:first_newline + 1] + header + context_md[first_newline + 1:]

        source = "deterministic"

    # Write context.md
    context_file.write_text(context_md)
    line_count = len(context_md.strip().split("\n"))
    print(f"context.md updated ({line_count} lines, {source})")

    # Update freshness state
    _write_last_run(reflect_dir, evidence["latest_checkpoint_id"], evidence["latest_git_sha"])

    return 0


def _run_legacy_harness(harness, args, context_file):
    """Legacy path: run .reflect/harness as subprocess."""
    print("Using legacy .reflect/harness (migrate to format.yaml with `reflect init --migrate`)", file=sys.stderr)

    max_lines = getattr(args, "max_lines", None)
    if not max_lines:
        config_file = Path(".reflect") / "config.yaml"
        if config_file.exists():
            match = re.search(r'^max_lines:\s*(\d+)', config_file.read_text(), re.MULTILINE)
            if match:
                max_lines = int(match.group(1))

    flags = []
    if max_lines:
        flags.extend(["--max-lines", str(max_lines)])

    harness_cmd = [str(harness)] if os.access(harness, os.X_OK) else [sys.executable, str(harness)]

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

    context_file.write_text(result.stdout)
    line_count = len(result.stdout.strip().split("\n"))
    print(f"context.md updated ({line_count} lines, legacy harness)")
    return 0
