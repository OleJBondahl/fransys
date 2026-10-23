"""Plain values from symdef's grid values: field copies, no arithmetic."""

from typing import cast, get_args

from symdef import GridBox
from symdef import Orientation as SymdefOrientation

from fransys_layout.core.values import Box, Orientation

__all__ = (
    "ORIENTATIONS",
    "symdef_orientation",
    "to_box",
)

ORIENTATIONS = cast("tuple[Orientation, ...]", get_args(Orientation))


def to_box(grid: GridBox) -> Box:
    """The core `Box` of a measured box, in the same grid divisions."""
    return Box(grid.min.x, grid.min.y, grid.width, grid.height)


def symdef_orientation(orient: Orientation) -> SymdefOrientation:
    """Symdef's orientation of the same name."""
    return SymdefOrientation(orient)
