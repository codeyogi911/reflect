"""reflect search — grep across all evidence sources."""

import json
import os
import shutil
import sys
from pathlib import Path

from .sources import get_entire_checkpoints, has_entire, has_git, run
from .wiki import read_page, scan_wiki_index


def _search_tokens(query, phrase):
    """Return non-empty search tokens. Default: split on whitespace, OR-match each token."""
    raw = query.strip()
    if not raw:
        return []
    if phrase:
        return [raw]
    seen = set()
    out = []
    for t in raw.split():
        k = t.lower()
        if t and k not in seen:
            seen.add(k)
            out.append(t)
    return out


def _has_qmd():
    """Return True if the qmd CLI is available."""
    return shutil.which("qmd") is not None


def _qmd_collection_name():
    """Derive a unique qmd collection name from the repo directory name."""
    return f"reflect-{Path.cwd().name}"


def _search_qmd(query, limit):
    """Search wiki via qmd hybrid search (BM25 + vector + reranking)."""
    cmd = [
        "qmd",
        "query",
        query,
        "-c",
        _qmd_collection_name(),
        "--json",
        "-n",
        str(limit),
    ]
    raw = run(cmd, timeout=60)
    if not raw:
        return []
    try:
        results = json.loads(raw)
        # qmd returns: [{"path": "...", "score": 0.9, "snippet": "..."}]
        return results
    except (json.JSONDecodeError, TypeError):
        return []


def _search_wiki_text(tokens, wiki_dir, limit):
    """Text-based wiki search. Returns list of match dicts sorted by score desc."""
    pages = scan_wiki_index(wiki_dir)
    matches = []

    for page in pages:
        # Pre-filter: check indexed fields first (cheap)
        tags_str = " ".join(page["tags"]) if isinstance(page["tags"], list) else str(page["tags"])
        cheap_text = (page["title"] + " " + page.get("summary", "") + " " + tags_str).lower()
        cheap_score = sum(1 for tok in tokens if tok.lower() in cheap_text)

        # Only read full body if cheap filter has partial match or query is short
        if cheap_score > 0 or len(tokens) <= 2:
            try:
                _, body = read_page(page["path"])
            except (OSError, UnicodeDecodeError):
                body = ""
            searchable = (page["title"] + " " + body + " " + tags_str).lower()
            score = sum(1 for tok in tokens if tok.lower() in searchable)
        else:
            score = 0

        if score > 0:
            matches.append(
                {
                    "rel_path": page["rel_path"],
                    "title": page["title"],
                    "summary": page["summary"],
                    "category": page["category"],
                    "tags": page["tags"],
                    "match_score": score,
                }
            )

    matches.sort(key=lambda m: m["match_score"], reverse=True)
    return matches[:limit]


def cmd_search(args):
    """Grep across all evidence sources for a query."""
    query = " ".join(args.query)
    if not query.strip():
        print("Usage: reflect search <query>", file=sys.stderr)
        return 1

    phrase = getattr(args, "phrase", False)
    limit = getattr(args, "limit", 10)
    as_json = getattr(args, "json", False)
    wiki_only = getattr(args, "wiki_only", False)
    tokens = _search_tokens(query, phrase)
    if not tokens:
        print("No search terms after parsing query.", file=sys.stderr)
        return 1

    # Locate wiki directory relative to cwd
    wiki_dir = Path(os.getcwd()) / ".reflect" / "wiki"
    wiki_exists = wiki_dir.exists()

    wiki_matches = []
    entire_matches = []
    git_matches = []

    # --- Wiki search (primary) ---
    if wiki_exists:
        if _has_qmd():
            wiki_matches = _search_qmd(query, limit)
        # Fall back to text search if qmd returns nothing (collection may not exist)
        if not wiki_matches:
            wiki_matches = _search_wiki_text(tokens, wiki_dir, limit)
    elif wiki_only:
        print("Wiki not initialized. Run `reflect init` first.", file=sys.stderr)
        return 1

    # --- Entire + git search (skip when --wiki-only) ---
    if not wiki_only:
        if has_entire():
            checkpoints = get_entire_checkpoints()
            for cp in checkpoints:
                searchable = cp["intent"]
                for c in cp["commits"]:
                    searchable += " " + c["message"]
                hay = searchable.lower()
                if any(tok.lower() in hay for tok in tokens):
                    entire_matches.append(cp)

        if has_git():
            cmd = ["git", "log", "--oneline", f"-{limit * 2}", "-i", "-F"]
            for tok in tokens:
                cmd.extend(["--grep", tok])
            git_output = run(cmd)
            if git_output:
                for line in git_output.split("\n"):
                    parts = line.split(" ", 1)
                    if len(parts) >= 2:
                        git_matches.append({"sha": parts[0], "message": parts[1]})
                    elif parts:
                        git_matches.append({"sha": parts[0], "message": ""})

    if as_json:
        # Normalize wiki matches to a consistent shape
        normalized_wiki = []
        for m in wiki_matches:
            if "rel_path" in m:
                normalized_wiki.append(m)
            else:
                # qmd shape → normalize
                normalized_wiki.append(
                    {
                        "rel_path": m.get("path", ""),
                        "title": "",
                        "summary": m.get("snippet", ""),
                        "category": "",
                        "tags": [],
                        "match_score": m.get("score", 0),
                    }
                )

        result = {
            "query": query,
            "tokens": tokens,
            "wiki_matches": normalized_wiki,
            "entire_matches": [
                {
                    "checkpoint_id": cp["id"],
                    "date": cp["date"],
                    "intent": cp["intent"],
                    "commits": cp["commits"],
                }
                for cp in entire_matches[:limit]
            ],
            "git_matches": git_matches[:limit],
            "total": len(wiki_matches) + len(entire_matches) + len(git_matches),
        }
        print(json.dumps(result, indent=2))
        return 0

    found = 0

    if wiki_matches:
        print(f"## Wiki Pages ({len(wiki_matches)} matches)\n")
        for m in wiki_matches:
            # qmd result shape: {"path": ..., "score": ..., "snippet": ...}
            # text result shape: {"rel_path": ..., "title": ..., "summary": ..., "tags": ...}
            if "rel_path" in m:
                tags = m.get("tags", [])
                tags_str = (
                    (", ".join(tags) if isinstance(tags, list) else str(tags)) if tags else ""
                )
                summary = m.get("summary", "")
                print(f"- [{m['rel_path']}] {summary}")
                if tags_str:
                    print(f"  Tags: {tags_str}")
            else:
                # qmd shape
                path = m.get("path", "")
                snippet = m.get("snippet", "")
                score = m.get("score", "")
                print(f"- [{path}] {snippet}" + (f" (score: {score:.2f})" if score else ""))
        print()
        found += len(wiki_matches)

    if entire_matches:
        print(f"## Entire Sessions ({len(entire_matches)} matches)\n")
        for cp in entire_matches[:limit]:
            commits_str = ""
            if cp["commits"]:
                commits_str = f" → {cp['commits'][0]['message'][:60]}"
            print(f"- [{cp['id'][:12]}] ({cp['date']}) {cp['intent'][:100]}{commits_str}")
        if len(entire_matches) > limit:
            print(f"  ... {len(entire_matches) - limit} more (use --limit to show more)")
        print()
        found += len(entire_matches)

    if git_matches:
        print(f"## Git Commits ({len(git_matches)} matches)\n")
        for g in git_matches[:limit]:
            print(f"- {g['sha']} {g['message']}")
        if len(git_matches) > limit:
            print(f"  ... {len(git_matches) - limit} more (use --limit to show more)")
        print()
        found += len(git_matches)

    if found == 0:
        if len(tokens) == 1:
            print(f"No matches for {tokens[0]!r}.")
        else:
            print(
                f"No matches (OR across {len(tokens)} terms: {', '.join(repr(t) for t in tokens)})."
            )
        return 0

    print(f"---\n{found} total matches across all sources.")
    return 0
