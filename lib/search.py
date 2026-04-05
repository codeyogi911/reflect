"""reflect search — grep across all evidence sources."""

import json
import sys

from .sources import has_entire, has_git, get_entire_checkpoints, run


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


def cmd_search(args):
    """Grep across all evidence sources for a query."""
    query = " ".join(args.query)
    if not query.strip():
        print("Usage: reflect search <query>", file=sys.stderr)
        return 1

    phrase = getattr(args, "phrase", False)
    limit = getattr(args, "limit", 10)
    as_json = getattr(args, "json", False)
    tokens = _search_tokens(query, phrase)
    if not tokens:
        print("No search terms after parsing query.", file=sys.stderr)
        return 1

    entire_matches = []
    git_matches = []

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
        result = {
            "query": query,
            "tokens": tokens,
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
            "total": len(entire_matches) + len(git_matches),
        }
        print(json.dumps(result, indent=2))
        return 0

    found = 0

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
                f"No matches (OR across {len(tokens)} terms: "
                f"{', '.join(repr(t) for t in tokens)})."
            )
        return 0

    print(f"---\n{found} total matches across all sources.")
    return 0
