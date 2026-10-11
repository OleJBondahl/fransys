"""The alias and anchor walks end on a planted cycle (they had no guard before `follow`)."""

from typing import Any, cast

from fransys_layout.stages._ordering import _hangs_from

A, B, C, Z = (("a",), ("b",), ("c",), ("z",))


def test_a_column_does_not_hang_from_itself() -> None:
    """The start of the walk is not one of the columns it hangs from."""
    anchor = cast("Any", {A: B})
    assert not _hangs_from(A, A, anchor)
    assert _hangs_from(A, B, anchor)
