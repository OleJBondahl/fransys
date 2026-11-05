"""The strict-xfail tables of the tests still red on the core (FLIP-NOW F4)."""

import tomllib
from pathlib import Path
from typing import Any

import pytest

__all__ = ["EXCEPTIONS", "GAP_PREFIX", "field_raises", "gaps", "mark_gaps", "other_gaps"]

GAP_FILE = Path(__file__).parent / "field_cases" / "gap_flip.toml"
OTHER_FILE = Path(__file__).parent / "gap_flip_other.toml"
GAP_PREFIX = "tests/field_cases/"
EXCEPTIONS: dict[str, type[BaseException]] = {
    e.__name__: e for e in (AssertionError, ValueError, KeyError, IndexError, StopIteration, pytest.fail.Exception)
}


def gaps() -> dict[str, Any]:
    """Field-case test id (below `tests/field_cases/`) to its `GAP-FLIP-<n>` row."""
    table: dict[str, Any] = tomllib.loads(GAP_FILE.read_text(encoding="utf-8"))["gaps"]
    return table


def field_raises(test_id: str) -> type[BaseException]:
    """The exception a field case's defect raises: its `[raises]` entry, else `AssertionError` (R1342)."""
    table: dict[str, Any] = tomllib.loads(GAP_FILE.read_text(encoding="utf-8")).get("raises", {})
    return EXCEPTIONS[table.get(test_id, "AssertionError")]


def other_gaps() -> dict[str, Any]:
    """Full test id of every other red test to its `GAP-FLIP-<n>` row."""
    table: dict[str, Any] = tomllib.loads(OTHER_FILE.read_text(encoding="utf-8"))["gaps"]
    return table


def mark_gaps(items: list[pytest.Item]) -> None:
    """A strict xfail, its reason naming the row and, for a field case, its `raises=`, on each listed case."""
    field, other = gaps(), other_gaps()
    for item in items:
        test_id = item.nodeid.removeprefix(GAP_PREFIX)
        gap = other.get(item.nodeid) or field.get(test_id)
        if gap is not None:
            raises = None if item.nodeid in other else field_raises(test_id)
            item.add_marker(pytest.mark.xfail(strict=True, raises=raises, reason=f"{gap}: red on the core"), append=False)
