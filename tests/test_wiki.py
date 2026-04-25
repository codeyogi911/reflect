"""Pure-Python tests for the wiki module helpers (no subprocess, no LLM)."""

from __future__ import annotations

from pathlib import Path

from reflect.wiki import parse_frontmatter, read_page, slugify, write_page


def test_slugify_basics() -> None:
    # Heuristic: drop "key"/"critical"/"important" prefix and "& X" suffix.
    assert slugify("Key Decisions & Rationale") == "decisions"
    assert slugify("Open Work") == "open-work"
    assert slugify("Critical Pitfalls") == "pitfalls"
    assert slugify("Gotchas & Friction") == "gotchas"


def test_slugify_strips_separators() -> None:
    assert slugify("foo - bar") == "foo"
    assert slugify("alpha & beta") == "alpha"
    assert slugify("Hello — World") == "hello"


def test_slugify_empty_returns_general() -> None:
    assert slugify("") == "general"
    assert slugify("   ") == "general"


def test_parse_frontmatter_roundtrip() -> None:
    raw = """---
title: Sample Page
created: 2026-01-01
updated: 2026-01-02
status: active
---

Body text here.
"""
    fm, body = parse_frontmatter(raw)
    assert fm["title"] == "Sample Page"
    assert fm["status"] == "active"
    assert body.strip() == "Body text here."


def test_parse_frontmatter_no_frontmatter() -> None:
    fm, body = parse_frontmatter("Just body, no frontmatter.\n")
    assert fm == {}
    assert "Just body" in body


def test_write_then_read_page(tmp_path: Path) -> None:
    page = tmp_path / "decisions" / "test.md"
    fm = {"title": "Test", "created": "2026-01-01", "status": "active"}
    body = "## Heading\n\nContent."
    write_page(page, fm, body)
    assert page.exists()
    out_fm, out_body = read_page(page)
    assert out_fm["title"] == "Test"
    assert "Content." in out_body
