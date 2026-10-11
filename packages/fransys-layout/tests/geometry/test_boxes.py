"""`geometry.boxes`."""

import pytest

from fransys_layout.geometry import (
    Box,
    GeometryError,
    overlaps,
)


def test_a_negative_size_raises_and_zero_is_allowed() -> None:
    """A box cannot be inside out; a degenerate one is a legal value."""
    assert Box(x=0, y=0, width=0, height=0).width == 0
    with pytest.raises(GeometryError):
        Box(x=0, y=0, width=-1, height=8)
    with pytest.raises(GeometryError):
        Box(x=0, y=0, width=8, height=-1)


def test_a_zero_area_box_overlaps_nothing() -> None:
    """A degenerate box has no interior, even when it lies inside another box."""
    outer = Box(x=0, y=0, width=32, height=32)
    zero_width = Box(x=8, y=8, width=0, height=8)
    zero_height = Box(x=8, y=8, width=8, height=0)
    for degenerate in (zero_width, zero_height):
        assert not overlaps(outer, degenerate)
        assert not overlaps(degenerate, outer)
    assert overlaps(outer, Box(x=8, y=8, width=1, height=1))
