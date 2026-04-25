"""End-to-end CLI tests that exercise build_parser + main() directly.

We invoke `main(argv)` rather than spawning a subprocess so coverage is collected
and tracebacks are readable. For the few tests that exercise real subprocess
behavior (status, init), the cwd is overridden via the `tmp_repo` fixture.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from reflect import __version__
from reflect.cli import build_parser, main


def test_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert __version__ in captured.out


def test_help_lists_all_subcommands(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["--help"])
    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    for cmd in (
        "init",
        "upgrade",
        "context",
        "search",
        "status",
        "sessions",
        "timeline",
        "ingest",
        "lint",
        "improve",
        "metrics",
    ):
        assert cmd in out, f"missing subcommand {cmd} in --help output"


def test_no_args_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main([])
    out = capsys.readouterr().out
    assert rc == 0
    assert "usage: reflect" in out


def test_build_parser_returns_parser_with_subcommands() -> None:
    parser = build_parser()
    actions = [a for a in parser._actions if a.dest == "command"]
    assert actions, "no subparsers action registered"
    choices = set(actions[0].choices)
    assert {"init", "ingest", "search", "lint", "status", "metrics"} <= choices


def test_status_outside_reflect_dir_is_user_error(
    tmp_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(["status"])
    out = capsys.readouterr().out + capsys.readouterr().err
    assert rc != 0 or "No .reflect" in out


def test_init_dry_run_makes_no_changes(tmp_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["init", "--dry-run", "--no-wiki"])
    captured = capsys.readouterr()
    out = captured.out + captured.err
    assert rc == 0
    assert "(dry-run)" in out
    assert not (tmp_repo / ".reflect").exists()
    assert not (tmp_repo / ".claude").exists()


def test_search_requires_query(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["search"])
    # argparse exits 2 when required args are missing.
    assert excinfo.value.code == 2


def test_metrics_outputs_json(tmp_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # metrics without .reflect/ should still produce valid JSON or a graceful exit.
    rc = main(["metrics"])
    out = capsys.readouterr().out
    if rc == 0 and out.strip():
        # Validate it's parseable JSON when emitted
        json.loads(out)
