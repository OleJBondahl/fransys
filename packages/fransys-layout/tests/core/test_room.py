"""Room and joined: the room beyond a footprint, and the per-field maximum (layout-0377)."""

from __future__ import annotations

from fransys_layout.core import Room, joined


def test_joined_takes_the_larger_value_of_each_field() -> None:
    assert joined(Room(1, 2, 3, 1), Room(4, 0, 2, 9), Room(0, 0, 0, 4)) == Room(4, 2, 3, 9)


def test_joined_of_nothing_is_no_room() -> None:
    assert joined() == Room()
    assert joined(Room(5, 6, 7, 8)) == Room(5, 6, 7, 8)
