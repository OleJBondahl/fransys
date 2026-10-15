"""Layout-0246: a fan-out whose split stands on a wire turns to a side clear of it."""

from typing import TYPE_CHECKING

from fransys_layout.geometry import WIRING_GRID, Facing, Point

from .line_side import across_by_room, clear_column, fan_clear, split_in
from .space import End

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from fransys_layout.geometry import Box

    from .harness_route import Grid, LineEnd
    from .line_draw import EndOnPage, Fan

    Drawn = tuple[EndOnPage, LineEnd, Fan | None]


def off_wires(
    drawn: Sequence[Drawn],
    grid: Grid,
    most: int,
    redraw: Callable[[EndOnPage, tuple[Facing, int]], Drawn],
) -> list[Drawn]:
    """Each fan whose split stands on a wire, or in a keep-out, turns to a side clear of both.

    `redraw` draws the end again turned to `(side, grids)`, up to `most` grids. One grid across
    is level with the pins.
    """
    found = list(drawn)
    obstacles = grid.obstacles
    for index, (one, _, fan) in enumerate(drawn):
        if fan is None or (fan_clear(fan, grid.wires) and not split_in(fan, obstacles)):
            continue
        sides = across_by_room(fan.facing, fan.at, grid.region)
        tries = (
            redraw(one, (side, grids))
            for side, first in ((fan.facing, 1), *((side, 2) for side in sides))
            for grids in range(first, most + 1)
        )
        found[index] = next(
            (t for t in tries if fan_clear(t[2], grid.wires, obstacles)), found[index]
        )
    return found


def _plug_end(box: Box, mate: Box | None, toward: tuple[int, int] | None = None) -> End:
    """A plug box's edge middle away from the box it mates, on the grid: up unless it is below.

    A plug-less box (layout-0206) takes the edge facing the rows of the line's other ends.
    """
    below = mate is not None and mate.y + mate.height <= box.y
    if toward is not None:
        below = toward[0] >= box.y + box.height
    x = box.x + box.width // 2
    x -= x % WIRING_GRID
    if below:
        y = box.y + box.height
        return End(at=Point(x=x, y=y + (-y) % WIRING_GRID), facing=Facing.S)
    return End(at=Point(x=x, y=box.y - box.y % WIRING_GRID), facing=Facing.N)


def box_end(one: EndOnPage, box: Box, grid: Grid) -> End:
    """The plug box end slid to a column whose run out touches no wire (layout-0246)."""
    return clear_column(
        _plug_end(box, one.mate, one.toward),
        box,
        grid.stub if one.leaving else None,
        grid.wires,
        grid.obstacles,
    )
