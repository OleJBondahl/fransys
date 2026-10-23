"""A symbol's reach in its row: its footprint plus its room, on the wiring grid (R408, R409).

The y solve keeps rows apart by it and the spans measure by it, so a band and its spans are one
measure (R377, R386).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .room import Room
    from .values import Box, Options


def grid_up(value: int, step: int) -> int:
    """Round up to the wiring grid, so every pin lands on it."""
    return -(-value // step) * step


def row_top(reach: int, options: Options) -> int:
    """How far a row's top lies above the origin of a symbol whose footprint reaches `reach` up."""
    return grid_up(reach, options.wiring_grid)


def extent(footprint: Box, room: Room, options: Options) -> tuple[int, int]:
    """The G a symbol's row holds above and below its origin; `footprint` is relative to it."""
    up = row_top(-footprint.y + room.up, options)
    return up, grid_up(footprint.y + footprint.h + room.down, options.wiring_grid)
