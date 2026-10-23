"""The strict-xfail tables of the tests still red on the core (FLIP-NOW F4)."""

import tomllib
from pathlib import Path

import pytest

__all__ = ["GAP_PREFIX", "INTERNAL_FILE", "gaps", "internal_gaps", "mark_gaps", "other_gaps"]

GAP_FILE = Path(__file__).parent / "field_cases" / "gap_flip.toml"
OTHER_FILE = Path(__file__).parent / "gap_flip_other.toml"
INTERNAL_FILE = Path(__file__).parents[1] / "internal" / "tests" / "gap_flip_internal.toml"
GAP_PREFIX = "tests/field_cases/"


def gaps() -> dict[str, str]:
    """Field-case test id (below `tests/field_cases/`) to its `GAP-FLIP-<n>` row."""
    return tomllib.loads(GAP_FILE.read_text(encoding="utf-8"))["gaps"]


def other_gaps() -> dict[str, str]:
    """Full test id of every other red test to its `GAP-FLIP-<n>` row."""
    return tomllib.loads(OTHER_FILE.read_text(encoding="utf-8"))["gaps"]


def internal_gaps() -> dict[str, str]:
    """Full test id of every red internal test to its row; empty where `internal/` is absent."""
    if not INTERNAL_FILE.is_file():
        return {}
    return tomllib.loads(INTERNAL_FILE.read_text(encoding="utf-8"))["gaps"]


def mark_gaps(items: list[pytest.Item]) -> None:
    """A strict xfail, its reason naming the row, on each listed case."""
    field, other = gaps(), other_gaps() | internal_gaps()
    for item in items:
        gap = other.get(item.nodeid) or field.get(item.nodeid.removeprefix(GAP_PREFIX))
        if gap is not None:
            item.add_marker(
                pytest.mark.xfail(strict=True, reason=f"{gap}: red on the core"), append=False
            )
