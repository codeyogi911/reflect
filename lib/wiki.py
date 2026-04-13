"""Wiki layer utilities — frontmatter, page I/O, index scanning, index.md management.

The wiki lives at .reflect/wiki/ with subdirectories per format.yaml section
(plus dynamic categories created by the ingest triage agent).
Each page is a markdown file with YAML frontmatter (created, updated, sources,
tags, status, related).  A committed index.md provides a browsable table of
contents, updated after every ingest.
"""

import re
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Slugify
# ---------------------------------------------------------------------------

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


def slugify(name):
    """Convert a section name to a directory-safe slug.

    "Key Decisions & Rationale" → "decisions"
    "Gotchas & Friction"        → "gotchas"
    "Open Work"                 → "open-work"
    "Critical Pitfalls"         → "pitfalls"

    Heuristic: drop leading adjectives (key, critical) and trailing
    clarifications (& rationale) to get short, memorable slugs.
    """
    low = name.lower().strip()

    # Drop common leading adjectives
    for prefix in ("key ", "critical ", "important "):
        if low.startswith(prefix):
            low = low[len(prefix):]

    # Drop anything after &, —, or –
    for sep in (" & ", " — ", " – ", " - "):
        if sep in low:
            low = low.split(sep)[0]

    # Replace non-alnum runs with hyphens
    slug = _SLUG_STRIP.sub("-", low).strip("-")
    return slug or "general"


# ---------------------------------------------------------------------------
# Frontmatter parsing / writing
# ---------------------------------------------------------------------------

def parse_frontmatter(text):
    """Parse YAML frontmatter from markdown text.

    Returns (frontmatter_dict, body_text).  If no frontmatter found,
    returns ({}, full_text).
    """
    if not text.startswith("---"):
        return {}, text

    end = text.find("\n---", 3)
    if end < 0:
        return {}, text

    raw_fm = text[4:end]  # skip opening ---\n
    body = text[end + 4:].lstrip("\n")  # skip closing ---\n

    fm = {}
    current_key = None
    current_list = None

    for line in raw_fm.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # List item under current key
        if stripped.startswith("- ") and current_list is not None:
            item = stripped[2:].strip()
            # Handle "key: value" items in source lists
            if ": " in item and current_key == "sources":
                k, v = item.split(": ", 1)
                current_list.append({k.strip(): v.strip()})
            else:
                current_list.append(item)
            continue

        # Key: value
        if ": " in stripped or stripped.endswith(":"):
            if ": " in stripped:
                key, val = stripped.split(": ", 1)
            else:
                key = stripped.rstrip(":")
                val = ""
            key = key.strip()
            val = val.strip()

            # Detect inline list: [a, b, c]
            if val.startswith("[") and val.endswith("]"):
                items = [x.strip().strip("'\"") for x in val[1:-1].split(",") if x.strip()]
                fm[key] = items
                current_key = key
                current_list = None
                continue

            if not val:
                # Start of a block list
                current_key = key
                current_list = []
                fm[key] = current_list
                continue

            fm[key] = val
            current_key = key
            current_list = None

    return fm, body


def render_frontmatter(fm):
    """Render a frontmatter dict back to YAML string (between --- fences)."""
    lines = ["---"]
    # Ordered keys for readability
    key_order = ["created", "updated", "sources", "tags", "status", "related"]
    keys = list(key_order) + [k for k in fm if k not in key_order]

    for key in keys:
        if key not in fm:
            continue
        val = fm[key]
        if isinstance(val, list):
            if not val:
                continue
            # Short lists of strings → inline
            if all(isinstance(x, str) for x in val) and len(val) <= 5:
                lines.append(f"{key}: [{', '.join(val)}]")
            else:
                lines.append(f"{key}:")
                for item in val:
                    if isinstance(item, dict):
                        for k, v in item.items():
                            lines.append(f"  - {k}: {v}")
                    else:
                        lines.append(f"  - {item}")
        else:
            lines.append(f"{key}: {val}")

    lines.append("---")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Page I/O
# ---------------------------------------------------------------------------

def read_page(page_path):
    """Read a wiki page.  Returns (frontmatter_dict, body_text)."""
    text = Path(page_path).read_text()
    return parse_frontmatter(text)


def write_page(page_path, fm, body):
    """Write a wiki page with frontmatter + body."""
    path = Path(page_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = render_frontmatter(fm) + "\n\n" + body.strip() + "\n"
    path.write_text(content)


# ---------------------------------------------------------------------------
# Wiki index (runtime scan of frontmatter)
# ---------------------------------------------------------------------------

def scan_wiki_index(wiki_dir):
    """Scan all wiki pages and return a list of page metadata dicts.

    Each entry: {path, category, filename, title, status, tags, updated, summary}
    where summary is the first non-heading, non-empty line of the body.
    """
    wiki_dir = Path(wiki_dir)
    pages = []

    if not wiki_dir.exists():
        return pages

    for md_file in sorted(wiki_dir.rglob("*.md")):
        # Skip log.md and _archive/
        if md_file.name == "log.md":
            continue
        if "_archive" in md_file.parts:
            continue

        rel = md_file.relative_to(wiki_dir)
        parts = rel.parts

        # Must be in a category subdirectory
        if len(parts) < 2:
            continue

        category = parts[0]
        fm, body = read_page(md_file)

        # Extract title from first heading or filename
        title = ""
        for line in body.split("\n"):
            if line.startswith("# "):
                title = line[2:].strip()
                break
        if not title:
            title = md_file.stem.replace("-", " ").title()

        # Extract one-line summary (first non-heading non-empty line)
        summary = ""
        for line in body.split("\n"):
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                summary = stripped[:150]
                break

        pages.append({
            "path": str(md_file),
            "rel_path": str(rel),
            "category": category,
            "filename": md_file.stem,
            "title": title,
            "status": fm.get("status", "active"),
            "tags": fm.get("tags", []),
            "updated": fm.get("updated", ""),
            "created": fm.get("created", ""),
            "sources": fm.get("sources", []),
            "related": fm.get("related", []),
            "summary": summary,
        })

    return pages


def build_index_summary(wiki_dir):
    """Build a concise text summary of all wiki pages for the ingest subagent.

    Returns a string like:
      decisions/declarative-format-yaml.md | active | Declarative format.yaml + Claude Subagent Synthesis
      pitfalls/yaml-parser-state-reset.md  | active | YAML-lite parser scoping bug...
    """
    pages = scan_wiki_index(wiki_dir)
    if not pages:
        return "(empty wiki — no existing pages)"

    lines = []
    for p in pages:
        status = p["status"]
        lines.append(f"{p['rel_path']} | {status} | {p['title']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Wiki directory setup
# ---------------------------------------------------------------------------

def init_wiki(reflect_dir, fmt_sections):
    """Create wiki/ directory structure from format.yaml sections.

    Returns the wiki_dir Path.
    """
    wiki_dir = Path(reflect_dir) / "wiki"
    wiki_dir.mkdir(exist_ok=True)

    # Create category subdirectories
    for section in fmt_sections:
        slug = slugify(section["name"])
        (wiki_dir / slug).mkdir(exist_ok=True)

    # Create empty log.md if it doesn't exist
    log_file = wiki_dir / "log.md"
    if not log_file.exists():
        log_file.write_text("# Wiki Ingest Log\n\n")

    return wiki_dir


def append_log(wiki_dir, entry_lines):
    """Append an ingest entry to log.md."""
    log_file = Path(wiki_dir) / "log.md"
    now = datetime.now().strftime("%Y-%m-%d")
    entry = f"\n## [{now}] ingest | {entry_lines[0]}\n"
    for line in entry_lines[1:]:
        entry += f"- {line}\n"

    with open(log_file, "a") as f:
        f.write(entry)


# ---------------------------------------------------------------------------
# index.md — committed table of contents
# ---------------------------------------------------------------------------

def update_index_md(wiki_dir):
    """Regenerate index.md from current wiki pages.

    Groups active pages by category with one-line summaries.
    Archived/resolved pages are excluded to keep the index bounded.
    """
    wiki_dir = Path(wiki_dir)
    pages = scan_wiki_index(wiki_dir)

    # Group by category
    by_category = {}
    for page in pages:
        if page["status"] not in ("active",):
            continue
        cat = page["category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(page)

    lines = [
        "# Knowledge Base Index",
        "",
        f"_Auto-generated by reflect — {len(pages)} active pages across "
        f"{len(by_category)} categories._",
        "",
    ]

    for cat in sorted(by_category.keys()):
        cat_pages = by_category[cat]
        # Sort by updated date, newest first
        cat_pages.sort(key=lambda p: p.get("updated", ""), reverse=True)

        lines.append(f"## {cat}")
        lines.append("")
        for page in cat_pages:
            summary = page.get("summary", "")
            if summary:
                summary = f" — {summary}"
            lines.append(f"- [{page['title']}]({page['rel_path']}){summary}")
        lines.append("")

    index_file = wiki_dir / "index.md"
    index_file.write_text("\n".join(lines))
