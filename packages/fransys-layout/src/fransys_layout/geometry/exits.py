"""A port's exit: its wire leaves one wiring grid along the port's facing (route.md, rule table)."""

from .symbols import Facing
from .units import WIRING_GRID, Point

# Facing to the page step of one wiring grid; the one table of the layout package.
FACING_STEP = frozendict(
    {
        Facing.N: (0, -WIRING_GRID),
        Facing.E: (WIRING_GRID, 0),
        Facing.S: (0, WIRING_GRID),
        Facing.W: (-WIRING_GRID, 0),
    }
)


def port_exit(at: Point, facing: Facing, grids: int = 1) -> Point:
    """The point `grids` wiring grids out of the port at `at` along `facing` (its first leg)."""
    dx, dy = FACING_STEP[facing]
    return Point(x=at.x + dx * grids, y=at.y + dy * grids)
