"""Layout units: the integer grid every stage, engine and record works in (design/geometry.md 5.1).

The symbol libraries draw in module units (M = 2.5 mm) on a 0.125 M drawing grid. The
layout unit is the grid unit `G = M/8`, so every library coordinate is an exact integer.
x grows right, y grows down, and a page origin is the top left of its content box.
"""

from electrical_symbols import G_PER_MODULE, WIRING_GRID
from fransys_model.kernel import value

from .errors import GeometryError

# A text stands this far from what it must not touch: a neighbour's text, a page edge.
TEXT_GAP = WIRING_GRID

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


def snap_up(coord: Coord, *, grid: int = WIRING_GRID) -> Coord:
    """Return the smallest multiple of `grid` that is `>= coord`."""
    return -(-coord // grid) * grid


def on_wiring_grid(point: Point) -> bool:
    """Whether both coordinates of `point` are multiples of `WIRING_GRID`."""
    return point.x % WIRING_GRID == 0 and point.y % WIRING_GRID == 0
