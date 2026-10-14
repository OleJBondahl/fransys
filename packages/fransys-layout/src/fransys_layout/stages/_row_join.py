"""Layout-0154: a path run on through a fan's further rows (line_draw.py)."""

from typing import TYPE_CHECKING

from .harness_route import LineEnd, line_paths
from .line_side import aside
from .space import End

if TYPE_CHECKING:
    from fransys_layout.geometry import Point

    from .harness_route import Grid
    from .line_draw import Fan


def _joined(points: tuple[Point, ...], fan: Fan, grid: Grid) -> tuple[Point, ...]:
    """`points` run on from whichever of its ends stands at `fan.at`, through `fan.rows`.

    The run may go back along the line's last run: drawn twice, it reads as the line's branch.
    """
    if points[-1] == fan.at:
        return (*points, *_row_run(fan, grid)[1:])
    if points[0] == fan.at:
        return (*reversed(_row_run(fan, grid)), *points[1:])
    return points


def _row_run(fan: Fan, grid: Grid) -> tuple[Point, ...]:
    """The run from `fan.at` through each further row's split, entered from outside.

    It leaves each split along its row, toward the next.
    """
    run: list[Point] = [fan.at]
    facing = fan.facing
    for end in fan.rows:
        start = End(run[-1], aside(run[-1], end.at, facing))
        run.extend(line_paths((LineEnd(0, start), LineEnd(0, end)), grid)[0][1:])
        facing = end.facing
    return tuple(run)
