"""reflect ingest — gather new evidence and write/update wiki pages.

Pipeline: evidence (fixed) → triage subagent (JSON plan) → write subagent (page content) → disk → qmd.
Two-step design: first decide what to do, then do it.  Avoids wasted writes.
The triage agent extracts ALL knowledge from sessions — decisions, preferences,
patterns, brand, business rules, gotchas, etc. — not just coding signals.
Categories are dynamic: the triage agent can propose new categories.
"""

import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from lib.evidence import gather_evidence, build_evidence_document, truncate_evidence
from lib.context import load_format
from lib.wiki import (
    slugify,
    build_index_summary,
    read_page,
    write_page,
    parse_frontmatter,
    append_log,
    update_index_md,
)


# ---------------------------------------------------------------------------
# Model / budget config
# ---------------------------------------------------------------------------

MODEL = os.environ.get("REFLECT_MODEL", "claude-haiku-4-5-20251001")
INGEST_BUDGET = os.environ.get("REFLECT_INGEST_BUDGET", "0.10")


# ---------------------------------------------------------------------------
# Freshness state (duplicated from context.py to avoid circular imports)
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
# qmd helpers
# ---------------------------------------------------------------------------

def _qmd_collection_name():
    """Derive a unique qmd collection name from the repo directory name."""
    return f"reflect-{Path.cwd().name}"


# ---------------------------------------------------------------------------
# Branch helpers (Strategy A: wiki belongs on the default branch)
# ---------------------------------------------------------------------------

def _get_current_branch():
    """Return the current git branch name, or None if not in a git repo."""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip() or None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def _get_default_branch():
    """Detect the repo's default branch (main, master, etc.).

    Tries `origin/HEAD` first (most reliable), then falls back to common names.
    Returns None if no default branch can be detected.
    """
    # Try origin/HEAD symbolic ref — this is what `git remote set-head` sets
    try:
        result = subprocess.run(
            ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            # e.g. "refs/remotes/origin/main" → "main"
            return result.stdout.strip().rsplit("/", 1)[-1]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Fall back to checking common default branch names
    for branch in ("main", "master", "trunk"):
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--verify", branch],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                return branch
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue

    return None


def _qmd_reindex(verbose=False):
    """Re-index the qmd collection after wiki changes.

    Runs `qmd update` (fast, updates BM25 index) and `qmd embed` (slow,
    generates vector embeddings). Embedding on CPU can take several minutes
    for large wikis — timeout is generous. Progress is shown on stderr.
    """
    collection = _qmd_collection_name()

    # qmd update is fast — BM25 index refresh only
    try:
        subprocess.run(
            ["qmd", "update", "-c", collection],
            capture_output=True, text=True, timeout=60, check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"  [ingest] qmd update failed: {e}", file=sys.stderr)
        return

    # qmd embed is slow on CPU — show live progress to stderr.
    # On headless/driverless machines, users may need QMD_LLAMA_GPU=false.
    print("  [ingest] Generating qmd embeddings (may take a few minutes)...", file=sys.stderr)
    try:
        result = subprocess.run(
            ["qmd", "embed", "-c", collection],
            stdout=sys.stderr, stderr=sys.stderr,
            timeout=900,  # 15 min — generous for CPU embedding
            check=False,
        )
        if result.returncode == 0:
            if verbose:
                print(f"  [ingest] qmd re-indexed: {collection}", file=sys.stderr)
        else:
            print(
                f"  [ingest] qmd embed failed (exit {result.returncode}). "
                f"If you're on a headless machine, try: QMD_LLAMA_GPU=false reflect ingest",
                file=sys.stderr,
            )
    except subprocess.TimeoutExpired:
        print(
            f"  [ingest] qmd embed timed out after 15 minutes. "
            f"If you're on a headless machine, try: QMD_LLAMA_GPU=false reflect ingest",
            file=sys.stderr,
        )
    except FileNotFoundError as e:
        print(f"  [ingest] qmd embed failed: {e}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Subagent helpers
# ---------------------------------------------------------------------------

def _strip_fences(text):
    """Strip markdown code fences if the model wrapped output in them."""
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.split("\n")
        # Drop opening fence line (```json, ```, etc.)
        start = 1
        # Drop closing fence if present
        end = len(lines)
        if lines[-1].strip() == "```":
            end -= 1
        return "\n".join(lines[start:end]).strip()
    return text


def _call_subagent(prompt, system_prompt, verbose=False, step_name=""):
    """Call the claude CLI with a prompt and system prompt.

    Returns the raw text output string, or None on failure.
    """
    if not shutil.which("claude"):
        print("  [ingest] claude CLI not found", file=sys.stderr)
        return None

    cmd = [
        "claude", "-p",
        "--model", MODEL,
        "--output-format", "json",
        "--max-turns", "1",
        "--tools", "",
        "--max-budget-usd", INGEST_BUDGET,
        "--setting-sources", "",
        "--no-session-persistence",
        "--system-prompt", system_prompt,
    ]

    label = f"[ingest/{step_name}]" if step_name else "[ingest]"
    if verbose:
        print(f"  {label} calling {MODEL} (budget ${INGEST_BUDGET})...", file=sys.stderr)

    try:
        result = subprocess.run(
            cmd, input=prompt, capture_output=True, text=True, timeout=180,
        )
    except subprocess.TimeoutExpired:
        print(f"  {label} timed out", file=sys.stderr)
        return None
    except OSError as e:
        print(f"  {label} failed to launch claude: {e}", file=sys.stderr)
        return None

    if result.returncode != 0:
        stderr_snippet = result.stderr[:200] if result.stderr else "(no stderr)"
        print(f"  {label} CLI exited {result.returncode}: {stderr_snippet}", file=sys.stderr)
        return None

    try:
        data = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError) as e:
        print(f"  {label} failed to parse CLI JSON output: {e}", file=sys.stderr)
        return None

    if data.get("is_error"):
        snippet = str(data.get("result", ""))[:200]
        print(f"  {label} CLI error: {snippet}", file=sys.stderr)
        return None

    raw = data.get("result", "")
    return _strip_fences(raw)


# ---------------------------------------------------------------------------
# Step 1 — Triage
# ---------------------------------------------------------------------------

_TRIAGE_SYSTEM = """\
You are a knowledge base curator. You receive session evidence (transcripts of \
human-AI coding sessions and git history) and an index of existing wiki pages. \
Your job is to extract ALL knowledge worth remembering and produce a JSON triage \
plan describing what wiki operations to perform.

WHAT TO EXTRACT — look for ANY of these signals in the evidence:
- Decisions: "we decided X because Y", "let's go with X", "X over Y because..."
- Preferences: user corrections, style choices, "I prefer X", "always do it this way"
- Patterns: coding patterns, conventions, "we always use X for Y"
- Gotchas: things that burned time, surprises, "watch out for X"
- Pitfalls: mistakes, reverts, failed approaches, "don't do X because Y"
- Architecture: how the system is structured, why components exist
- Business: pricing, brand, product decisions, domain knowledge
- Guides: deployment process, setup steps, workflows
- Open work: unfinished items, TODOs, "still need to..."
- ANY other project-specific knowledge that would be useful to remember

CATEGORIES — you may use existing categories or propose NEW ones. Use short, \
descriptive slugs: decisions, preferences, patterns, gotchas, pitfalls, \
architecture, business, brand, guides, open-work, conventions, etc. \
New categories are created automatically.

OUTPUT: Return ONLY valid JSON — no commentary, no markdown fences.

Schema:
{
  "create": [
    {"category": "<slug>", "slug": "<page-slug>", "title": "<Page Title>", "reason": "<why>"}
  ],
  "update": [
    {"path": "<category/page.md>", "reason": "<what changed>"}
  ],
  "resolve": [
    {"path": "<category/page.md>", "reason": "<completed in commit abc>"}
  ]
}

Rules:
- Use "create" for genuinely new knowledge not covered by any existing page.
- Use "update" for existing pages where the evidence adds new detail or changes understanding.
- Use "resolve" for open-work or in-progress pages that are now complete.
- Skip if evidence adds nothing new.
- Page slugs must be lowercase, hyphen-separated, descriptive (e.g. "database-choice", "deploy-process").
- Keep "reason" under 80 characters.
- Prefer updating existing pages over creating near-duplicates.
- Return {"create": [], "update": [], "resolve": []} if no changes are warranted."""


def _triage(evidence_doc, index_summary, categories, verbose=False):
    """Step 1: ask the subagent what pages to create/update/resolve.

    Returns parsed triage dict or None on failure.
    """
    cats_str = ", ".join(categories)
    prompt = (
        f"Existing wiki categories: {cats_str}\n"
        f"(You may also propose new categories — directories will be created automatically.)\n\n"
        f"Existing wiki pages:\n{index_summary}\n\n"
        f"New evidence to incorporate:\n\n{evidence_doc}"
    )

    raw = _call_subagent(prompt, _TRIAGE_SYSTEM, verbose=verbose, step_name="triage")
    if not raw:
        return None

    try:
        plan = json.loads(raw)
    except json.JSONDecodeError as e:
        if verbose:
            print(f"  [ingest/triage] JSON decode failed: {e}", file=sys.stderr)
            print(f"  [ingest/triage] raw: {raw[:300]}", file=sys.stderr)
        return None

    # Normalise keys to always be lists
    for key in ("create", "update", "resolve"):
        if key not in plan or not isinstance(plan[key], list):
            plan[key] = []

    # Validate create items have required fields
    plan["create"] = [
        c for c in plan["create"]
        if c.get("category") and c.get("slug") and c.get("title")
    ]

    # Validate update/resolve items have path
    for key in ("update", "resolve"):
        plan[key] = [item for item in plan[key] if item.get("path")]

    return plan


def _validate_triage(plan, categories, wiki_dir, verbose=False):
    """Validate triage plan against existing pages. Creates new category dirs on the fly."""

    # Allow dynamic categories — create dirs for new ones
    for item in plan.get("create", []):
        cat = item.get("category", "")
        cat_dir = wiki_dir / cat
        if not cat_dir.exists() and cat:
            cat_dir.mkdir(parents=True, exist_ok=True)
            if verbose:
                print(f"  [ingest/triage] created new category: {cat}/", file=sys.stderr)

    # Filter update/resolve to existing paths
    for key in ("update", "resolve"):
        filtered = []
        for item in plan[key]:
            if not (wiki_dir / item["path"]).exists():
                if verbose:
                    print(f"  [ingest/triage] rejected {key}: path not found '{item['path']}'", file=sys.stderr)
                continue
            filtered.append(item)
        plan[key] = filtered

    return plan


# ---------------------------------------------------------------------------
# Step 2 — Write
# ---------------------------------------------------------------------------

_WRITE_SYSTEM = """\
You are a knowledge base page writer. You receive session evidence (transcripts \
of human-AI coding sessions and git history) and a request to create or update a \
wiki page. Produce the COMPLETE page content: YAML frontmatter followed by \
markdown body.

FRONTMATTER (YAML between --- fences):
  created: YYYY-MM-DD      (use provided date for new pages; preserve original for updates)
  updated: YYYY-MM-DD      (today)
  sources: list of checkpoint IDs or commit SHAs cited (e.g. - checkpoint abc123, - commit def456)
  tags: list of 1-4 short topic tags
  status: active | resolved | abandoned
  related: list of related page rel_paths (optional)

BODY (markdown):
  - Start with a # Title heading
  - ~200-500 words, focused, factual
  - Use second-level headers (##) to organise if needed
  - Include specific evidence citations inline: (checkpoint <id>) or (commit <sha>)
  - Capture the SPECIFIC knowledge: exact values, names, reasons, preferences
  - No fluff, no generic advice — only project-specific knowledge
  - For preferences: record the exact preference and any reasoning given
  - For decisions: record what was chosen, what was rejected, and why
  - For patterns: record the pattern, when to use it, and examples if available

OUTPUT: Return ONLY the raw page content (frontmatter + body). No commentary. No fences."""


def _write_page_content(evidence_doc, action_type, page_info, existing_content, today, verbose=False):
    """Step 2 (per-page): ask the subagent to write or update a page.

    action_type: "create" | "update" | "resolve"
    page_info: dict from triage plan
    existing_content: str or None (None for create)

    Returns raw page text or None on failure.
    """
    if action_type == "create":
        context_block = (
            f"Create a NEW wiki page.\n"
            f"Category: {page_info['category']}\n"
            f"Title: {page_info['title']}\n"
            f"Reason: {page_info['reason']}\n"
            f"Today's date: {today}\n"
        )
    elif action_type == "update":
        existing_block = existing_content or "(no existing content)"
        context_block = (
            f"UPDATE the following existing wiki page.\n"
            f"Page path: {page_info['path']}\n"
            f"Reason: {page_info['reason']}\n"
            f"Today's date: {today}\n\n"
            f"--- EXISTING PAGE ---\n{existing_block}\n--- END EXISTING PAGE ---\n"
        )
    else:  # resolve
        existing_block = existing_content or "(no existing content)"
        context_block = (
            f"RESOLVE the following wiki page — mark it as completed/resolved.\n"
            f"Page path: {page_info['path']}\n"
            f"Reason: {page_info['reason']}\n"
            f"Today's date: {today}\n\n"
            f"--- EXISTING PAGE ---\n{existing_block}\n--- END EXISTING PAGE ---\n"
        )

    prompt = (
        f"{context_block}\n\n"
        f"Evidence to draw from:\n\n{evidence_doc}"
    )

    return _call_subagent(prompt, _WRITE_SYSTEM, verbose=verbose, step_name="write")


def _batch_write(evidence_doc, actions, action_type, wiki_dir, today, verbose=False):
    """Write pages concurrently using a thread pool.

    Returns list of (item, raw_content, effective_action_type) tuples.
    Each action is a dict from the triage plan.
    """
    MAX_WORKERS = 5
    results = []

    def _write_one(item):
        action_type_eff = action_type
        existing = None

        if action_type in ("update", "resolve"):
            page_path = wiki_dir / item["path"]
            if page_path.exists():
                existing = page_path.read_text()
            else:
                if verbose:
                    print(
                        f"  [ingest/write] page not found: {item['path']}, treating as create",
                        file=sys.stderr,
                    )
                action_type_eff = "create"
                # Fill in category/title from path for create fallback
                parts = item["path"].split("/")
                item_copy = dict(item)
                if "category" not in item_copy:
                    item_copy["category"] = parts[0] if parts else "general"
                if "title" not in item_copy:
                    item_copy["title"] = parts[-1].replace(".md", "").replace("-", " ").title()
                if "slug" not in item_copy:
                    item_copy["slug"] = parts[-1].replace(".md", "") if parts else "page"
                return item_copy, action_type_eff, existing

        return item, action_type_eff, existing

    # Prepare items (read existing content) — fast, sequential
    prepared = [_write_one(item) for item in actions]

    # Call subagent for each page concurrently
    def _call_one(prep):
        item, action_type_eff, existing = prep
        raw = _write_page_content(
            evidence_doc, action_type_eff,
            item, existing, today, verbose=verbose,
        )
        return item, raw, action_type_eff

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(_call_one, p): p for p in prepared}
        for future in as_completed(futures):
            item, raw, action_type_eff = future.result()
            if raw:
                results.append((item, raw, action_type_eff))
            else:
                label = item.get("path") or f"{item.get('category')}/{item.get('slug')}"
                print(f"  [ingest/write] skipped {label} (subagent returned nothing)", file=sys.stderr)

    return results


# ---------------------------------------------------------------------------
# Page path resolution
# ---------------------------------------------------------------------------

def _resolve_page_path(wiki_dir, action_type, item):
    """Compute the filesystem path for a page from a triage action dict.

    For "create": wiki_dir / category / slug.md
    For "update"/"resolve": wiki_dir / item["path"]

    Validates that the resolved path stays within wiki_dir.
    """
    wiki_dir = Path(wiki_dir).resolve()

    if action_type == "create":
        cat = item.get("category", "general")
        slug = item.get("slug", "page")
        filename = slug if slug.endswith(".md") else slug + ".md"
        candidate = (wiki_dir / cat / filename).resolve()
    else:
        candidate = (wiki_dir / item["path"]).resolve()

    try:
        candidate.relative_to(wiki_dir)
    except ValueError:
        raise ValueError(f"Path traversal rejected: {item.get('path', item.get('slug', ''))}")

    return candidate


# ---------------------------------------------------------------------------
# Parse subagent page output into (fm, body)
# ---------------------------------------------------------------------------

def _parse_page_output(raw, action_type, item, today):
    """Parse raw subagent output into (frontmatter_dict, body_str).

    If the model didn't produce valid frontmatter, synthesise a minimal one.
    """
    fm, body = parse_frontmatter(raw)

    # Ensure required fields
    if "created" not in fm:
        if action_type == "create":
            fm["created"] = today
        else:
            # Try to preserve from existing
            fm["created"] = today

    fm["updated"] = today

    if "status" not in fm:
        fm["status"] = "resolved" if action_type == "resolve" else "active"
    elif action_type == "resolve":
        fm["status"] = "resolved"

    if "tags" not in fm:
        fm["tags"] = []

    if "sources" not in fm:
        fm["sources"] = []

    return fm, body


# ---------------------------------------------------------------------------
# Main command
# ---------------------------------------------------------------------------

def cmd_ingest(args):
    """Ingest new evidence into the wiki."""
    reflect_dir = Path(".reflect")
    wiki_dir = reflect_dir / "wiki"
    verbose = getattr(args, "verbose", False)
    force = getattr(args, "force", False)

    # Guard: .reflect/ must exist
    if not reflect_dir.exists():
        print("No .reflect/ directory found. Run `reflect init` first.", file=sys.stderr)
        return 1

    # Guard: wiki/ must exist
    if not wiki_dir.exists():
        print(
            "No .reflect/wiki/ directory found. Run `reflect init` first.",
            file=sys.stderr,
        )
        return 1

    # Guard: claude CLI must be available
    if not shutil.which("claude"):
        print(
            "claude CLI not found. Install Claude Code to use `reflect ingest`.",
            file=sys.stderr,
        )
        return 1

    # --- Branch policy: wiki belongs on the default branch ---
    # Strategy A: warn (don't block) when ingesting on a non-default branch.
    # The wiki is project memory and should not fork along feature branches.
    current_branch = _get_current_branch()
    default_branch = _get_default_branch()
    if current_branch and default_branch and current_branch != default_branch and not force:
        print(
            f"Warning: ingesting on '{current_branch}' (default branch: '{default_branch}').",
            file=sys.stderr,
        )
        print(
            f"  Wiki updates here will not appear on other branches until merged.",
            file=sys.stderr,
        )
        print(
            f"  Recommended workflow: merge feature branches into '{default_branch}',",
            file=sys.stderr,
        )
        print(
            f"  then run 'reflect ingest' on '{default_branch}' to update canonical knowledge.",
            file=sys.stderr,
        )
        print(
            f"  Use --force to suppress this warning.",
            file=sys.stderr,
        )
        print(file=sys.stderr)

    today = datetime.now().strftime("%Y-%m-%d")

    # --- Load format to know seeded categories ---
    fmt = load_format(reflect_dir)
    categories = [slugify(s["name"]) for s in fmt.get("sections", [])]
    # Also include any existing wiki subdirectories (dynamic categories)
    for d in wiki_dir.iterdir():
        if d.is_dir() and not d.name.startswith("_") and d.name not in categories:
            categories.append(d.name)

    # --- Read high-water mark from .last_run ---
    last_run_file = reflect_dir / ".last_run"
    since_sha = None
    since_checkpoint = None
    is_seed = True  # first ingest ever

    if last_run_file.exists():
        try:
            lr = json.loads(last_run_file.read_text())
            since_sha = lr.get("last_git_sha") or None
            since_checkpoint = lr.get("last_checkpoint") or None
            if since_sha or since_checkpoint:
                is_seed = False
        except (json.JSONDecodeError, OSError):
            pass

    # First seed: large window to capture full history
    # Subsequent: only new evidence since last ingest
    if is_seed:
        max_cp, max_commits = 100, 200
        print("Gathering evidence (initial seed — full history)...", file=sys.stderr)
    else:
        max_cp, max_commits = 30, 50
        print("Gathering evidence (incremental)...", file=sys.stderr)

    evidence = gather_evidence(
        max_checkpoints=max_cp,
        max_commits=max_commits,
        since_sha=since_sha,
        since_checkpoint=since_checkpoint,
    )

    total_cp = evidence["stats"]["total_checkpoints"]
    total_commits = evidence["stats"]["total_commits"]
    print(f"Found {total_cp} checkpoints, {total_commits} commits", file=sys.stderr)

    if total_cp == 0 and total_commits == 0:
        print("No new evidence since last ingest.")
        return 0

    evidence_doc = build_evidence_document(evidence)
    evidence_doc = truncate_evidence(evidence_doc)

    # --- Build wiki index summary ---
    index_summary = build_index_summary(wiki_dir)
    if verbose:
        print(f"  [ingest] wiki index:\n{index_summary}", file=sys.stderr)

    # --- Step 1: Triage ---
    print("Step 1/2: Triaging wiki changes...", file=sys.stderr)
    plan = _triage(evidence_doc, index_summary, categories, verbose=verbose)

    if plan is None:
        print("Triage failed — no changes written.", file=sys.stderr)
        return 1

    plan = _validate_triage(plan, categories, wiki_dir, verbose=verbose)

    n_create = len(plan.get("create", []))
    n_update = len(plan.get("update", []))
    n_resolve = len(plan.get("resolve", []))
    total_ops = n_create + n_update + n_resolve

    print(
        f"Plan: {n_create} create, {n_update} update, {n_resolve} resolve",
        file=sys.stderr,
    )

    if total_ops == 0:
        print("Nothing to do — wiki is already up to date.")
        _write_last_run(reflect_dir, evidence["latest_checkpoint_id"], evidence["latest_git_sha"])
        return 0

    # --- Step 2: Write ---
    print("Step 2/2: Writing wiki pages...", file=sys.stderr)

    wiki_dir_abs = wiki_dir.resolve()
    written = []   # list of (rel_path, action_type) for log
    errors = []

    for action_type in ("create", "update", "resolve"):
        actions = plan.get(action_type, [])
        if not actions:
            continue

        results = _batch_write(evidence_doc, actions, action_type, wiki_dir, today, verbose=verbose)

        for item, raw_content, eff_action_type in results:
            page_path = _resolve_page_path(wiki_dir, eff_action_type, item)

            # Preserve original created date for updates/resolves
            original_created = None
            if action_type in ("update", "resolve") and page_path.exists():
                try:
                    orig_fm, _ = read_page(page_path)
                    original_created = orig_fm.get("created")
                except Exception:
                    pass

            fm, body = _parse_page_output(raw_content, action_type, item, today)

            if original_created:
                fm["created"] = original_created

            try:
                write_page(page_path, fm, body)
                rel = str(page_path.relative_to(wiki_dir_abs))
                written.append((rel, action_type))
                verb = {"create": "created", "update": "updated", "resolve": "resolved"}[action_type]
                print(f"  {verb}: {rel}", file=sys.stderr)
            except Exception as e:
                label = str(page_path)
                print(f"  [ingest] failed to write {label}: {e}", file=sys.stderr)
                errors.append(label)

    # --- Update log.md ---
    if written:
        summary_line = f"{len(written)} page(s) — {n_create} created, {n_update} updated, {n_resolve} resolved"
        detail_lines = [f"{verb} {rel}" for rel, verb in written]
        append_log(wiki_dir, [summary_line] + detail_lines)

    # --- Update index.md ---
    if written:
        update_index_md(wiki_dir)
        if verbose:
            print("  [ingest] index.md updated", file=sys.stderr)

    # --- Update qmd index ---
    if written and shutil.which("qmd"):
        _qmd_reindex(verbose=verbose)

    # --- Update freshness state ---
    _write_last_run(reflect_dir, evidence["latest_checkpoint_id"], evidence["latest_git_sha"])

    # --- Report ---
    n_written = len(written)
    n_errors = len(errors)
    parts = []
    if n_written:
        parts.append(f"{n_written} page(s) written")
    if n_errors:
        parts.append(f"{n_errors} error(s)")
    print(", ".join(parts) if parts else "Done.")

    return 0 if not errors else 1
