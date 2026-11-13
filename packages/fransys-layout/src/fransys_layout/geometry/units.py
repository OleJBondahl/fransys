"""Layout units: the integer grid every stage, engine and record works in.

The symbol libraries draw in module units (M = 2.5 mm) on a 0.125 M drawing grid. The
layout unit is the grid unit `G = M/8`, so every library coordinate is an exact integer.
x grows right, y grows down, and a page origin is the top left of its content box.
"""

from electrical_symbols import WIRING_GRID
from fransys_model.kernel import value

type Coord = int


@value
class Point:
    """A position in grid units."""

    x: int
    y: int


PAGE_PAD = 2 * WIRING_GRID  # clear space between the frame line and a page's ink (layout-0187)
