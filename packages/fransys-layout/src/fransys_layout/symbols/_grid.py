"""Plain values from symdef's grid values: field copies, and a reach grown outward to the grid (R1693)."""

from typing import cast, get_args

from symdef import GridBox
from symdef import Orientation as SymdefOrientation

from fransys_layout.core import grid_out
from fransys_layout.core.values import Box, Orientation

__all__ = (
    "ORIENTATIONS",
    "symdef_orientation",
    "to_box",
    "to_reach",
)

ORIENTATIONS = cast("tuple[Orientation, ...]", get_args(Orientation))


def to_box(grid: GridBox) -> Box:
    """The core `Box` of a measured box, in the same grid divisions."""
    return Box(grid.min.x, grid.min.y, grid.width, grid.height)


def to_reach(grid: GridBox, pitch: int) -> Box:
    """The core `Box` of a keep-out, grown to whole `pitch` cells by core `grid_out`: layout reads a reach only on the grid (R1693)."""
    return grid_out(to_box(grid), pitch)


def symdef_orientation(orient: Orientation) -> SymdefOrientation:
    """Symdef's orientation of the same name."""
    return SymdefOrientation(orient)
