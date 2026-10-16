"""A port's exit: its wire leaves one wiring grid along the port's facing."""

from fransys_layout.core.sides import SIDE_STEP

from .symbols import Facing
from .units import WIRING_GRID, Point

# Facing to the page step of one wiring grid, read from the core's side table (layout-0306).
FACING_STEP = frozendict(
    {Facing[side]: (dx * WIRING_GRID, dy * WIRING_GRID) for side, (dx, dy) in SIDE_STEP.items()}
)


def port_exit(at: Point, facing: Facing, grids: int = 1) -> Point:
    """The point `grids` wiring grids out of the port at `at` along `facing` (its first leg)."""
    dx, dy = FACING_STEP[facing]
    return Point(x=at.x + dx * grids, y=at.y + dy * grids)
