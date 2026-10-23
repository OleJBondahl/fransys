"""The one side table: the clockwise order N E S W and the unit step of each side.

Turning a side, its opposite and the step it points along all read this table (layout-0306).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .values import Side

# Insertion order is clockwise from north; y grows down, so N steps towards smaller y.
SIDE_STEP: frozendict[Side, tuple[int, int]] = frozendict(
    {"N": (0, -1), "E": (1, 0), "S": (0, 1), "W": (-1, 0)}
)
CLOCKWISE: tuple[Side, ...] = tuple(SIDE_STEP)


def opposite(side: Side) -> Side:
    """The side across: N and S, E and W."""
    return CLOCKWISE[(CLOCKWISE.index(side) + 2) % 4]


def step_out(side: Side, x: int, y: int, length: int) -> tuple[int, int]:
    """The point `length` out from (x, y) along `side`: a stub's end, a marker box's stand."""
    dx, dy = SIDE_STEP[side]
    return x + dx * length, y + dy * length
