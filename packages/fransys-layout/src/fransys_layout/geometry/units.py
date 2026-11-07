"""Layout units: the integer grid every stage, engine and record works in.

The symbol libraries draw in module units (M = 2.5 mm) on a 0.125 M drawing grid. The
layout unit is the grid unit `G = M/8`, so every library coordinate is an exact integer.
x grows right, y grows down, and a page origin is the top left of its content box.
"""

from electrical_symbols import G_PER_MODULE, WIRING_GRID
from fransys_model.kernel import value

from .errors import GeometryError

type Coord = int


@value
class Point:
    """A position in grid units."""

    x: int
    y: int


def to_grid(module_units: float) -> Coord:
    """Convert a library coordinate in module units to grid units."""
    grid_units = module_units * G_PER_MODULE
    if not grid_units.is_integer():
        msg = f"module units must be a multiple of 0.125, got {module_units!r}"
        raise GeometryError(msg)
    return int(grid_units)


PAGE_PAD = 2 * WIRING_GRID  # clear space between the frame line and a page's ink (layout-0187)
