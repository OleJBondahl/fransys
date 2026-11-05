"""R550: the markers of one fan's two Refs are two groups, so two stars never join (el-0071)."""

from typing import Any

from fransys_el.write_markers import _groups

from fransys_layout.core import Marker, PinRef

PIN = PinRef("A", "p")
ARROW: Any = "arrow"  # the core RefKind member, which the surface does not export


def _arrow(ref: int, page: int) -> Marker:
    return Marker("f:x", ARROW, page, "1A", 0, 0, PIN, "R0", ref)


def test_a_fans_two_cuts_are_two_groups() -> None:
    markers = [_arrow(1, 1), _arrow(1, 2), _arrow(5, 2), _arrow(5, 2)]
    got = _groups(markers)
    assert sorted(len(g) for g in got.values()) == [2, 2]
    assert {k[1] for k in got} == {1, 5}
