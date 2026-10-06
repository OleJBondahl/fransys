"""The alias and anchor walks end on a planted cycle (they had no guard before `follow`)."""

from types import SimpleNamespace
from typing import Any, cast

from fransys_layout.stages._chain_reach import _home
from fransys_layout.stages._ordering import _hangs_from

A, B, C, Z = (("a",), ("b",), ("c",), ("z",))


def test_home_ends_on_an_alias_cycle() -> None:
    """A merged-into loop 1 -> 2 -> 3 -> 1 ends at its last new group."""
    r = cast("Any", SimpleNamespace(alias={1: 2, 2: 3, 3: 1}))
    assert _home(r, 1) == 3
    assert _home(r, 9) == 9


def test_hangs_from_ends_on_an_anchor_cycle() -> None:
    """An anchor loop is walked once: it reaches a root on it and ends for one off it."""
    anchor = cast("Any", {A: B, B: C, C: A})
    assert _hangs_from(A, C, anchor)
    assert not _hangs_from(A, Z, anchor)


def test_a_column_does_not_hang_from_itself() -> None:
    """The start of the walk is not one of the columns it hangs from."""
    anchor = cast("Any", {A: B})
    assert not _hangs_from(A, A, anchor)
    assert _hangs_from(A, B, anchor)
