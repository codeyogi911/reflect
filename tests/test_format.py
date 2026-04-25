"""Unit tests for the format.yaml loader (yaml-lite parser)."""

from __future__ import annotations

from pathlib import Path

from reflect.context import DEFAULT_FORMAT, load_format


def test_load_format_returns_default_when_missing(tmp_path: Path) -> None:
    fmt = load_format(tmp_path)
    assert fmt == DEFAULT_FORMAT
    # Must be a copy, not the singleton — mutation should not bleed.
    fmt["sections"].clear()
    assert DEFAULT_FORMAT["sections"], "DEFAULT_FORMAT was mutated"


def test_load_format_parses_user_overrides(tmp_path: Path) -> None:
    (tmp_path / "format.yaml").write_text(
        """\
sections:
  - name: My Custom Section
    purpose: testing
    max_bullets: 3
    recency: 7d
  - name: Another One
    purpose: also testing
    max_bullets: 5
    recency: 14d
citations: optional
max_lines: 200
"""
    )
    fmt = load_format(tmp_path)
    assert fmt["citations"] == "optional"
    assert fmt["max_lines"] == 200
    names = [s["name"] for s in fmt["sections"]]
    assert names == ["My Custom Section", "Another One"]
    assert fmt["sections"][0]["max_bullets"] == 3
    assert fmt["sections"][0]["recency"] == "7d"


def test_load_format_parses_entry_fields(tmp_path: Path) -> None:
    (tmp_path / "format.yaml").write_text(
        """\
sections:
  - name: Pitfalls
    purpose: known mistakes
    max_bullets: 8
    recency: 90d
    entry_fields:
      - mistake
      - consequence
      - rule
"""
    )
    fmt = load_format(tmp_path)
    assert fmt["sections"][0]["entry_fields"] == ["mistake", "consequence", "rule"]


def test_load_format_ignores_comments(tmp_path: Path) -> None:
    (tmp_path / "format.yaml").write_text(
        """\
# Top-level comment
sections:
  # Another comment
  - name: Foo
    purpose: bar
    max_bullets: 2
    recency: 30d
"""
    )
    fmt = load_format(tmp_path)
    assert len(fmt["sections"]) == 1
    assert fmt["sections"][0]["name"] == "Foo"
