"""reflect why — active query, dumps raw evidence to stdout."""

import sys
from .sources import (
    has_entire, has_git, get_entire_checkpoints,
    get_entire_transcript, get_checkpoint_for_commit, get_notes, run
)
from pathlib import Path


def _query_words(query):
    """Split query into lowercase words for flexible matching."""
    return [w for w in query.lower().split() if len(w) >= 2]


def _matches_text(words, text, require_all=True):
    """Check if query words appear in text.

    require_all=True: all words must match (AND)
    require_all=False: any word can match (OR)
    """
    text_lower = text.lower()
    if require_all:
        return all(w in text_lower for w in words)
    return any(w in text_lower for w in words)


def _print_checkpoint(cp, transcript=None):
    """Print a single checkpoint match."""
    print(f"### Session {cp['id'][:12]} ({cp['date']})")
    intent = cp["intent"]
    # Don't print giant context preambles as intent
    if len(intent) > 200 or intent.startswith("##"):
        first_line = intent.split("\n")[0][:120]
        print(f"**Intent**: {first_line}...")
    else:
        print(f"**Intent**: {intent}")
    if cp["commits"]:
        for c in cp["commits"]:
            print(f"**Commit**: `{c['sha']}` {c['message']}")
    print()

    if transcript:
        print("**Transcript (excerpt)**:")
        print("```")
        print(transcript)
        print("```")
        print()


def _search_entire(words, query, require_all=True):
    """Search Entire sessions with 3-pass strategy. Returns list of matches."""
    checkpoints = get_entire_checkpoints()
    metadata_matches = []
    metadata_ids = set()

    # Pass 1: fast metadata search (intent + commit messages)
    for cp in checkpoints:
        searchable = cp["intent"].lower()
        for c in cp["commits"]:
            searchable += " " + c["message"].lower()
        if _matches_text(words, searchable, require_all=require_all):
            metadata_matches.append(cp)
            metadata_ids.add(cp["id"])

    # Pass 2: search transcripts for unmatched checkpoints
    transcript_matches = []
    if len(metadata_matches) < 3:
        unmatched = [cp for cp in checkpoints if cp["id"] not in metadata_ids]
        for cp in unmatched[:20]:
            transcript = get_entire_transcript(cp["id"], max_lines=200)
            if transcript and _matches_text(words, transcript, require_all=require_all):
                transcript_matches.append((cp, transcript))
                if len(transcript_matches) >= 5:
                    break

    # Pass 3: search commits from all branches and look up their checkpoints
    # This catches sessions from squash-merged feature branches
    commit_matches = []
    seen_cp_ids = metadata_ids | {cp["id"] for cp, _ in transcript_matches}
    if len(metadata_matches) + len(transcript_matches) < 3:
        # Try each query word as a separate git grep term
        seen_shas = set()
        for word in words:
            git_shas = run(["git", "log", "--all", "--oneline", "-20",
                            "--format=%h", f"--grep={word}", "-i"])
            if git_shas:
                for sha in git_shas.strip().split("\n"):
                    sha = sha.strip()
                    if not sha or sha in seen_shas:
                        continue
                    seen_shas.add(sha)
                    cp = get_checkpoint_for_commit(sha)
                    if cp and cp["id"] not in seen_cp_ids:
                        seen_cp_ids.add(cp["id"])
                        transcript = get_entire_transcript(cp["id"], max_lines=200)
                        commit_matches.append((cp, transcript))
                        if len(commit_matches) >= 3:
                            break
            if len(commit_matches) >= 3:
                break

    return metadata_matches + transcript_matches + commit_matches


def cmd_why(args):
    """Fetch raw evidence matching a query and dump to stdout."""
    query = " ".join(args.query)
    if not query:
        print("Usage: reflect why <file-or-topic>", file=sys.stderr)
        return 1

    words = _query_words(query)
    found_anything = False

    # Search Entire sessions — metadata first, then transcripts, then cross-branch
    if has_entire():
        all_matches = _search_entire(words, query)

        # If AND matching found nothing and we have multiple words, retry with OR
        if not all_matches and len(words) > 1:
            all_matches = _search_entire(words, query, require_all=False)

        if all_matches:
            found_anything = True
            print(f"## Entire Sessions matching '{query}' ({len(all_matches)} found)\n")

            for item in all_matches[:5]:
                if isinstance(item, tuple):
                    cp, transcript = item
                    relevant = _extract_relevant_lines(transcript, words, context=15) if transcript else None
                    _print_checkpoint(cp, relevant)
                else:
                    transcript = get_entire_transcript(item["id"], max_lines=80)
                    _print_checkpoint(item, transcript)

    # Search git history — search all branches, not just current
    if has_git():
        if "/" in query or "." in query:
            git_output = run(["git", "log", "--all", "--oneline", "-20",
                              "--format=%h %ad %s", "--date=short", "--", query])
        else:
            git_output = run(["git", "log", "--all", "--oneline", "-20",
                              "--format=%h %ad %s", "--date=short",
                              f"--grep={query}", "-i"])

        if git_output:
            found_anything = True
            print(f"## Git History matching '{query}'\n")
            for line in git_output.split("\n")[:15]:
                print(f"- {line}")
            print()

        if "/" in query or "." in query:
            blame = run(["git", "log", "--all", "--oneline", "-10", "--follow", "--", query])
            if blame:
                print(f"## File History: {query}\n")
                for line in blame.split("\n")[:10]:
                    print(f"- {line}")
                print()

    # Search notes
    notes_dir = Path(".reflect/notes")
    notes = get_notes(notes_dir)
    matching_notes = [n for n in notes
                      if _matches_text(words, n["content"]) or _matches_text(words, n["name"])]
    if matching_notes:
        found_anything = True
        print(f"## Notes matching '{query}'\n")
        for note in matching_notes:
            print(f"### {note['name']}")
            print(note["content"][:500])
            print()

    if not found_anything:
        print(f"No evidence found for '{query}'.")
        if not has_entire():
            print("Tip: Install Entire CLI for richer session evidence.")
        return 1

    return 0


def _extract_relevant_lines(text, words, context=15):
    """Extract lines around the first match of query words in text."""
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if _matches_text(words, line):
            start = max(0, i - context)
            end = min(len(lines), i + context + 1)
            excerpt = lines[start:end]
            if start > 0:
                excerpt.insert(0, f"... (skipped {start} lines)")
            if end < len(lines):
                excerpt.append(f"... ({len(lines) - end} more lines)")
            return "\n".join(excerpt)
    # No single line has all words — return first chunk where any word appears
    for i, line in enumerate(lines):
        if any(w in line.lower() for w in words):
            start = max(0, i - context)
            end = min(len(lines), i + context + 1)
            excerpt = lines[start:end]
            if start > 0:
                excerpt.insert(0, f"... (skipped {start} lines)")
            if end < len(lines):
                excerpt.append(f"... ({len(lines) - end} more lines)")
            return "\n".join(excerpt)
    return text[:2000]
