"""reflect lint — wiki health check.

Scans the wiki and reports:
  1. Stale pages      — updated date older than category recency window
  2. Orphan pages     — no inbound related links from other pages
  3. Possibly resolved— open-work pages whose titles appear in recent git log
  4. Coverage gaps    — format.yaml sections with fewer than 2 wiki pages
  5. Near-duplicates  — pages in the same category with >70% title word overlap

--fix automatically:
  - Sets status: resolved on possibly-resolved open-work pages
  - Archives pages with status: superseded for >90 days to wiki/_archive/
"""

import json
import os
import re
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

from .context import load_format
from .sources import has_git, run
from .wiki import read_page, scan_wiki_index, slugify, write_page

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_recency(recency_str):
    """Parse a recency string like '30d', '14d', '90d' into a timedelta."""
    if not recency_str:
        return timedelta(days=30)
    match = re.match(r"(\d+)d", str(recency_str))
    return timedelta(days=int(match.group(1))) if match else timedelta(days=30)


def _parse_date(date_str):
    """Parse an ISO date string (YYYY-MM-DD) into a date object, or None."""
    if not date_str:
        return None
    try:
        return datetime.strptime(str(date_str).strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def _title_similarity(a, b):
    """Compute simple word-overlap similarity between two title strings.

    Returns a float in [0, 1] — higher means more similar.
    """
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    if not words_a or not words_b:
        return 0.0
    overlap = len(words_a & words_b)
    return overlap / max(len(words_a), len(words_b))


def _title_keywords(title):
    """Extract meaningful keywords from a title for git log search.

    Drops very short (≤2 char) and common stop words.
    """
    STOP = {
        "a",
        "an",
        "the",
        "and",
        "or",
        "in",
        "on",
        "of",
        "to",
        "for",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "with",
        "from",
        "at",
        "by",
        "as",
        "it",
        "its",
        "that",
        "this",
        "not",
        "no",
        "do",
        "did",
    }
    words = [w for w in re.split(r"[^a-z0-9]+", title.lower()) if len(w) > 2 and w not in STOP]
    return words


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def _check_stale(pages, fmt):
    """Return issues for pages whose updated date exceeds category recency window."""
    issues = []
    today = datetime.now().date()

    # Build a map: category slug → recency timedelta
    recency_by_cat = {}
    for section in fmt.get("sections", []):
        slug = slugify(section.get("name", ""))
        recency_by_cat[slug] = _parse_recency(section.get("recency", "30d"))

    for page in pages:
        cat = page["category"]
        recency = recency_by_cat.get(cat, timedelta(days=30))
        updated = _parse_date(page.get("updated", ""))
        if updated is None:
            # No updated date — treat as potentially stale with a note
            issues.append(
                {
                    "type": "stale",
                    "path": page["rel_path"],
                    "detail": f"No updated date (recency window: {recency.days}d)",
                }
            )
            continue
        age = today - updated
        if age > recency:
            issues.append(
                {
                    "type": "stale",
                    "path": page["rel_path"],
                    "detail": f"Updated {updated} ({age.days}d ago, recency window: {recency.days}d)",
                }
            )
    return issues


def _check_orphans(pages):
    """Return issues for pages with no inbound related links from other pages."""
    issues = []

    # Build set of pages that are referenced by at least one other page
    referenced = set()
    for page in pages:
        related = page.get("related", [])
        if isinstance(related, list):
            for ref in related:
                # Normalise: ref may or may not include leading category dir
                ref = str(ref).strip()
                referenced.add(ref)
                # Also try matching without .md suffix
                if ref.endswith(".md"):
                    referenced.add(ref[:-3])
                else:
                    referenced.add(ref + ".md")

    for page in pages:
        rel = page["rel_path"]
        rel_no_ext = rel[:-3] if rel.endswith(".md") else rel
        if rel not in referenced and rel_no_ext not in referenced:
            issues.append(
                {
                    "type": "orphan",
                    "path": rel,
                    "detail": "No inbound related links from other pages",
                }
            )
    return issues


def _check_possibly_resolved(pages):
    """Return issues for open-work pages whose title keywords appear in recent git log."""
    issues = []
    if not has_git():
        return issues

    # Fetch last 50 commits' short SHAs + messages
    git_log = run(
        [
            "git",
            "log",
            "-50",
            "--format=%h %s",
        ]
    )
    if not git_log:
        return issues

    # Build list of (sha, message) for fast iteration
    commits = []
    for line in git_log.split("\n"):
        parts = line.split(" ", 1)
        if len(parts) == 2:
            commits.append((parts[0], parts[1]))

    for page in pages:
        # Only check active open-work pages
        if page.get("status", "active") != "active":
            continue
        if page["category"] != slugify("Open Work"):
            continue

        keywords = _title_keywords(page["title"])
        if len(keywords) < 2:
            continue  # Too few keywords → too many false positives

        matching_shas = []
        for sha, msg in commits:
            msg_lower = msg.lower()
            # Require at least 2 keyword matches (or 1 if only 1 keyword)
            hits = sum(1 for kw in keywords if kw in msg_lower)
            threshold = min(2, len(keywords))
            if hits >= threshold:
                matching_shas.append(sha)

        if matching_shas:
            sha_list = ", ".join(matching_shas[:5])
            suffix = f" (+{len(matching_shas) - 5} more)" if len(matching_shas) > 5 else ""
            issues.append(
                {
                    "type": "possibly-resolved",
                    "path": page["rel_path"],
                    "detail": f"Keywords found in recent commits: {sha_list}{suffix}",
                    "_matching_shas": matching_shas,  # kept for --fix use
                }
            )
    return issues


def _check_coverage_gaps(pages, fmt):
    """Return issues for format.yaml sections with fewer than 2 wiki pages."""
    issues = []

    # Count pages per category slug
    counts = {}
    for page in pages:
        counts[page["category"]] = counts.get(page["category"], 0) + 1

    for section in fmt.get("sections", []):
        slug = slugify(section.get("name", ""))
        count = counts.get(slug, 0)
        if count < 2:
            issues.append(
                {
                    "type": "coverage-gap",
                    "category": slug,
                    "detail": f"Only {count} page{'s' if count != 1 else ''} (min recommended: 2)",
                }
            )
    return issues


def _check_near_duplicates(pages):
    """Return issues for pages in the same category with >70% title word overlap."""
    issues = []
    THRESHOLD = 0.70

    # Group by category
    by_cat = {}
    for page in pages:
        cat = page["category"]
        by_cat.setdefault(cat, []).append(page)

    for _cat, cat_pages in by_cat.items():
        n = len(cat_pages)
        for i in range(n):
            for j in range(i + 1, n):
                a = cat_pages[i]
                b = cat_pages[j]
                score = _title_similarity(a["title"], b["title"])
                if score > THRESHOLD:
                    issues.append(
                        {
                            "type": "near-duplicate",
                            "paths": [a["rel_path"], b["rel_path"]],
                            "detail": f"{int(score * 100)}% title overlap",
                        }
                    )
    return issues


# ---------------------------------------------------------------------------
# --fix actions
# ---------------------------------------------------------------------------


def _fix_resolved_pages(possibly_resolved_issues, wiki_dir):
    """Mark possibly-resolved open-work pages as status: resolved."""
    fixed = []
    for issue in possibly_resolved_issues:
        page_path = Path(wiki_dir) / issue["path"]
        if not page_path.exists():
            continue
        try:
            fm, body = read_page(page_path)
            if fm.get("status") == "active":
                fm["status"] = "resolved"
                fm["updated"] = datetime.now().strftime("%Y-%m-%d")
                write_page(page_path, fm, body)
                fixed.append(issue["path"])
        except (OSError, UnicodeDecodeError) as exc:
            print(f"  warn: could not fix {issue['path']}: {exc}", file=sys.stderr)
    return fixed


def _fix_archive_superseded(pages, wiki_dir):
    """Move pages with status: superseded for >90 days to wiki/_archive/."""
    ARCHIVE_AFTER = timedelta(days=90)
    today = datetime.now().date()
    archived = []
    archive_dir = Path(wiki_dir) / "_archive"

    for page in pages:
        if page.get("status") != "superseded":
            continue
        updated = _parse_date(page.get("updated", "")) or _parse_date(page.get("created", ""))
        if updated is None:
            continue
        if today - updated < ARCHIVE_AFTER:
            continue

        src = Path(page["path"])
        dst = archive_dir / page["category"] / src.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(src), str(dst))
            archived.append(page["rel_path"])
        except (OSError, shutil.Error) as exc:
            print(f"  warn: could not archive {page['rel_path']}: {exc}", file=sys.stderr)

    return archived


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def _print_report(issues, fix_log):
    """Print human-readable wiki health report."""
    stale = [i for i in issues if i["type"] == "stale"]
    orphans = [i for i in issues if i["type"] == "orphan"]
    resolved = [i for i in issues if i["type"] == "possibly-resolved"]
    gaps = [i for i in issues if i["type"] == "coverage-gap"]
    dupes = [i for i in issues if i["type"] == "near-duplicate"]

    print("## Wiki Health Report")
    print()

    # Stale
    print(f"### Stale Pages ({len(stale)})")
    if stale:
        for issue in stale:
            print(f"- {issue['path']} — {issue['detail']}")
    else:
        print("- none")
    print()

    # Orphans
    print(f"### Orphan Pages ({len(orphans)})")
    if orphans:
        for issue in orphans:
            print(f"- {issue['path']} — no inbound links")
    else:
        print("- none")
    print()

    # Possibly resolved
    print(f"### Possibly Resolved ({len(resolved)})")
    if resolved:
        for issue in resolved:
            print(f"- {issue['path']} — keywords in commits: {issue['detail'].split(': ', 1)[-1]}")
    else:
        print("- none")
    print()

    # Coverage gaps
    print(f"### Coverage Gaps ({len(gaps)})")
    if gaps:
        for issue in gaps:
            print(f"- {issue['category']} — {issue['detail']}")
    else:
        print("- none")
    print()

    # Near-duplicates
    print(f"### Near-Duplicates ({len(dupes)})")
    if dupes:
        for issue in dupes:
            paths = issue["paths"]
            print(f"- {paths[0]} \u2194 {paths[1]} — {issue['detail']}")
    else:
        print("- none")
    print()

    # Fix log
    if fix_log:
        print("### Auto-Fixed")
        for entry in fix_log:
            print(f"- {entry}")
        print()

    total = len(issues)
    print("---")
    print(f"{total} issue{'s' if total != 1 else ''} found")


def _issues_for_json(issues):
    """Strip private keys (prefixed with _) before JSON output."""
    clean = []
    for issue in issues:
        clean.append({k: v for k, v in issue.items() if not k.startswith("_")})
    return clean


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def cmd_lint(args):
    """Check wiki health and report issues."""
    as_json = getattr(args, "json", False)
    do_fix = getattr(args, "fix", False)

    reflect_dir = Path(os.getcwd()) / ".reflect"
    wiki_dir = reflect_dir / "wiki"

    if not reflect_dir.exists():
        print("No .reflect/ directory. Run `reflect init` first.", file=sys.stderr)
        return 1

    if not wiki_dir.exists():
        print("No wiki found. Run `reflect init` first.", file=sys.stderr)
        return 1

    # Load pages + format config
    pages = scan_wiki_index(wiki_dir)
    fmt = load_format(reflect_dir)

    if not pages:
        if as_json:
            print(json.dumps({"issues": [], "total": 0}))
        else:
            print("## Wiki Health Report\n\nWiki is empty — no pages to lint.")
        return 0

    # Run all checks
    issues = []
    issues.extend(_check_stale(pages, fmt))
    issues.extend(_check_orphans(pages))
    issues.extend(_check_possibly_resolved(pages))
    issues.extend(_check_coverage_gaps(pages, fmt))
    issues.extend(_check_near_duplicates(pages))

    # Apply fixes if requested
    fix_log = []
    if do_fix:
        possibly_resolved = [i for i in issues if i["type"] == "possibly-resolved"]
        if possibly_resolved:
            fixed = _fix_resolved_pages(possibly_resolved, wiki_dir)
            for path in fixed:
                fix_log.append(f"marked resolved: {path}")

        archived = _fix_archive_superseded(pages, wiki_dir)
        for path in archived:
            fix_log.append(f"archived: {path}")

    # Output
    if as_json:
        output = {
            "issues": _issues_for_json(issues),
            "total": len(issues),
        }
        if fix_log:
            output["fixed"] = fix_log
        print(json.dumps(output, indent=2))
    else:
        _print_report(issues, fix_log)

    # Non-zero exit when issues found (useful for CI)
    return 1 if issues and not do_fix else 0
