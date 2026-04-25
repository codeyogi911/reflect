"""Sanity tests for the exit-code module."""

from reflect import exit_codes


def test_exit_codes_are_distinct() -> None:
    codes = {
        exit_codes.OK,
        exit_codes.USER_ERROR,
        exit_codes.ENV_ERROR,
        exit_codes.UPSTREAM_ERROR,
    }
    assert len(codes) == 4


def test_ok_is_zero() -> None:
    assert exit_codes.OK == 0
