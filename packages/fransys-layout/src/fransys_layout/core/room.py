"""Room: what a placed symbol's drawn things need beyond its footprint (layout-0377)."""

from __future__ import annotations

from typing import NamedTuple


class Room(NamedTuple):
    """The G a row's fitted boxes reach beyond a pin to the left, right, up and down."""

    left: int = 0
    right: int = 0
    up: int = 0
    down: int = 0


def joined(*rooms: Room) -> Room:
    """The largest value of each field over the rooms given; empty with none."""
    return Room(*(max((r[i] for r in rooms), default=0) for i in range(4)))
