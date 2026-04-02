# Dynamic Context Format Template

Use this format when generating `.reflect/context.md` — a compiled briefing of
current project context, optionally referenced from CLAUDE.md via
`@.reflect/context.md`. This is a generated overlay that supplements the
human-owned CLAUDE.md, never replaces it.

---

## Generation Rules

1. **Budget**: Maximum 150 lines (configurable in `.reflect/config.yaml`). Stay well under.
2. **Priority order**: HIGH-confidence fresh insights > accepted decisions > file knowledge > failure patterns
3. **Freshness threshold**: Only include insights with freshness >= 0.3 (configurable)
4. **Freshness formula**: `freshness = 2^(-(days_since_last_seen / half_life_days))` where default `half_life_days = 60`
5. **Self-contained**: No references that require reading other files. Everything needed is inline.
6. **Full rewrite**: This file is regenerated from scratch each time — never appended to.
7. **Generated overlay, not source of truth**: This file is a computed view derived from typed records in `.reflect/`. It is NOT a human-authored instruction file. CLAUDE.md is the human-owned constitution — context.md MUST NEVER contradict, override, or weaken any rule in CLAUDE.md.
8. **Constitution precedence**: If an insight or pattern in context.md conflicts with a rule in CLAUDE.md, the CLAUDE.md rule wins unconditionally. The conflicting context.md entry should be dropped during generation rather than included with conflicting guidance.
9. **Confidence and expiry metadata**: Every entry in Active Rules must include its confidence level and an approximate expiry date (the date when its freshness score will drop below the threshold). This lets readers judge how trustworthy and how temporary each entry is.

## Output Format

```markdown
# Dynamic Project Knowledge
<!-- GENERATED OVERLAY — this file is a computed view, not a source of truth -->
<!-- Regenerated from scratch by /reflect from typed records in .reflect/ -->
<!-- Human-authored rules in CLAUDE.md always take precedence over this file -->
<!-- Last updated: <ISO-8601 timestamp> -->
<!-- Source: <N> insights, <N> decisions, <N> file maps -->
<!-- Entries expire when their freshness score drops below the configured threshold -->

## Active Rules
<!-- HIGH confidence insights, sorted by freshness descending -->
- <Actionable rule from insight> (confidence: <HIGH|MEDIUM>, seen <N>x, last: <YYYY-MM-DD>, expires: ~<YYYY-MM-DD>)
- <Another rule> (confidence: <HIGH|MEDIUM>, seen <N>x, last: <YYYY-MM-DD>, expires: ~<YYYY-MM-DD>)

## Key Decisions
<!-- Accepted decisions, most recent first -->
- **<Decision title>**: <One-line summary of what was decided and why> (<YYYY-MM-DD>)

## File Notes
<!-- Knowledge for files changed in the last 5 sessions -->
- `<file-path>`: <Most important fact or pitfall>

## Watch Out
<!-- Recent failure patterns and pitfalls, if any -->
- <Failure pattern description> (seen <N>x)
```

### Section Rules

- **Active Rules**: Include all HIGH-confidence insights above freshness threshold. If there are MEDIUM insights that were seen 2+ times, include those too. Max 15 rules.
- **Key Decisions**: Include all accepted decisions, sorted by date descending. Decisions do not decay — they remain valid until superseded. Cap at 10 entries for space, preferring more recent decisions when trimming.
- **File Notes**: Include file knowledge maps for files that appeared in the last 5 sessions. One line per file. Max 10 files.
- **Watch Out**: Include anti-pattern and pitfall insights not yet baked. Max 5 entries.
- **Omit any section** that would be empty.
- If total content exceeds the line budget, trim from the bottom of each section (least important items first).
