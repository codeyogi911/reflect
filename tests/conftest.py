"""Shared pytest fixtures for the reflect test suite."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture
def tmp_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Create an empty git repo in a temp dir, chdir into it, and yield the path.

    Disables GPG signing so the seed commit succeeds in CI environments where
    signing is enforced. Restores the original cwd via monkeypatch.chdir.
    """
    monkeypatch.chdir(tmp_path)
    subprocess.run(["git", "init", "-q"], check=True, cwd=tmp_path)
    subprocess.run(["git", "config", "user.email", "test@example.com"], check=True, cwd=tmp_path)
    subprocess.run(["git", "config", "user.name", "Test"], check=True, cwd=tmp_path)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], check=True, cwd=tmp_path)
    subprocess.run(
        ["git", "-c", "commit.gpgsign=false", "commit", "--allow-empty", "-m", "seed"],
        check=True,
        cwd=tmp_path,
    )
    yield tmp_path


@pytest.fixture
def reflect_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset reflect-related env vars to known values for deterministic tests."""
    for var in ("REFLECT_MODEL", "REFLECT_CONTEXT_BUDGET", "REFLECT_INGEST_BUDGET"):
        monkeypatch.delenv(var, raising=False)
    # Avoid accidentally hitting the user's real reflect home.
    monkeypatch.setenv("REFLECT_HOME", os.devnull)
