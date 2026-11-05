"""A symbol's reach in its row: its footprint plus its room, on the wiring grid (R408, R409).

The y solve keeps rows apart by it and the spans measure by it, so a band and its spans are one
measure (R377, R386).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .values import Box

if TYPE_CHECKING:
    from .values import Options


def grid_up(value: int, step: int) -> int:
    """Round up to the wiring grid, so every pin lands on it."""
    return -(-value // step) * step


def grid_out(box: Box, step: int) -> Box:
    """`box` grown outward to whole `step` cells on every side: the one home for rounding a Box to the grid (R1693, R1706)."""
    x0, y0 = -grid_up(-box.x, step), -grid_up(-box.y, step)
    x1, y1 = grid_up(box.x + box.w, step), grid_up(box.y + box.h, step)
    return Box(x0, y0, x1 - x0, y1 - y0)


def row_top(reach: int, options: Options) -> int:
    """How far a row's top lies above the origin of a symbol whose footprint reaches `reach` up."""
    return grid_up(reach, options.wiring_grid)


def held(footprint: Box, options: Options) -> tuple[int, int]:
    """The G a symbol's row holds above and below its origin; `footprint` is relative to it."""
    return row_top(-footprint.y, options), grid_up(footprint.y + footprint.h, options.wiring_grid)
