"""HL15 and HL16 (layout-0154): a harness line's polylines and its label, pure, over given points.

The ends come in the ends row's order with their branch numbers (`derive.harness_line_ends`);
nothing here numbers. Every path is drawn by `grid_path`, the router's one search.
"""

from dataclasses import dataclass, replace
from itertools import pairwise
from typing import Any
lazy from collections.abc import Sequence

from fransys_layout.geometry import (
    FACING_STEP,
    OPPOSITE,
    WIRING_GRID,
    Box,
    Facing,
    LayoutError,
    Point,
    pad,
)
from fransys_layout.geometry.units import TEXT_GAP
lazy from fransys_model.kernel import Id

from .grid_path import Field, cells_of, grid_path
from .space import Cell, End, Obstacle, span
from .texts.candidates import TextKind
from .texts.place_texts import Anchor, PlacedText, TextToPlace

_NO_CELLS = frozenset[Cell]()


@dataclass(frozen=True, slots=True)
class LineEnd:
    """One end of a line: its branch from the ends row, its point and facing, at an interface."""

    branch: int
    end: End
    interface: bool = False


@dataclass(frozen=True, slots=True)
class Grid:
    """What a line's search sees: the page region it may use, its keep-outs, the turn cost."""

    region: Box
    obstacles: tuple[Obstacle, ...]
    turn_penalty: int


def root(ends: Sequence[LineEnd]) -> LineEnd:
    """HL15: the first end at a unit interface in the ends row's order, else the first end."""
    return next((one for one in ends if one.interface), ends[0])


def line_paths(ends: Sequence[LineEnd], grid: Grid) -> dict[int, tuple[Point, ...]]:
    """HL15: one polyline per end, keyed by its branch; the trunk is the root's.

    Two ends give one polyline, the root's. Legs leave the split in turn, each free to run
    along the cells of the legs before it, so overlapping legs share their runs.
    """
    first = root(ends)
    others = [one for one in ends if one is not first]
    if len(others) == 1:
        return {first.branch: _path(first.end, others[0].end, grid, _NO_CELLS, first.branch)}
    split = _split(first.end, [one.end for one in others])
    trunk_goal = End(at=split, facing=OPPOSITE[first.end.facing])
    paths = {first.branch: _path(first.end, trunk_goal, grid, _NO_CELLS, first.branch)}
    shared = _NO_CELLS
    for one in others:
        leg = _path(End(at=split, facing=first.end.facing), one.end, grid, shared, one.branch)
        shared |= cells_of(leg)
        paths[one.branch] = leg
    return paths


def _split(start: End, others: Sequence[End]) -> Point:
    """The split on the root's axis, half way to the nearest other end ahead, at least a grid."""
    dx, dy = FACING_STEP[start.facing]
    ahead = [(one.at.x - start.at.x) * dx + (one.at.y - start.at.y) * dy for one in others]
    # each reach is in grids times WIRING_GRID, as the step is one grid long
    nearest = min((reach for reach in ahead if reach > 0), default=0) // WIRING_GRID**2
    steps = max(nearest // 2, 1)
    return Point(x=start.at.x + dx * steps, y=start.at.y + dy * steps)


def _path(
    start: End, goal: End, grid: Grid, free: frozenset[Cell], branch: int
) -> tuple[Point, ...]:
    """One orthogonal run of `grid_path`, over the keep-outs when they shut it in.

    A line always draws: its end may stand where a text blocks its first step (layout-0154).
    A line not even the free region can draw is a layout error.
    """
    field = Field(
        region=grid.region,
        obstacles=grid.obstacles,
        free=free,
        busy=frozenset(),
        turn_penalty=grid.turn_penalty,
        crossing_penalty=0,
    )
    points = grid_path(start, goal, field) or grid_path(start, goal, replace(field, obstacles=()))
    if points is None:
        msg = f"no orthogonal path for harness line branch {branch}"
        raise LayoutError(msg)
    return _unspiked(points)


def _unspiked(points: tuple[Point, ...]) -> tuple[Point, ...]:
    """The path less each run that turns back on itself, so it stops on its ends (layout-0158).

    A search entering a joint from its facing side overshoots it and comes back.
    """
    out: list[Point] = []
    for point in points:
        while len(out) > 1 and _step(out[-1], point) in _axis(_step(out[-2], out[-1])):
            out.pop()
        if not out or out[-1] != point:
            out.append(point)
    return tuple(out)


def _step(one: Point, two: Point) -> tuple[int, int]:
    return (two.x > one.x) - (two.x < one.x), (two.y > one.y) - (two.y < one.y)


def _axis(step: tuple[int, int]) -> tuple[tuple[int, int], tuple[int, int]]:
    return step, (-step[0], -step[1])


def longest_run(points: tuple[Point, ...]) -> tuple[Point, Point]:
    """HL16: the polyline's longest straight run; the first of equal ones."""
    return max(
        pairwise(points), key=lambda run: abs(run[1].x - run[0].x) + abs(run[1].y - run[0].y)
    )


def line_text(
    harness: Id[Any], branch: int, points: tuple[Point, ...], size: tuple[int, int]
) -> TextToPlace:
    """HL16: a leg's designation to place, beside its longest run, for one `place_texts` call.

    Above a horizontal run, right of a vertical one, then the mirror (the `harness_line` row),
    the house text gap off the run (layout-0158).
    """
    first, second = longest_run(points)
    facing = Facing.N if first.y == second.y else Facing.E
    return TextToPlace(
        kind=TextKind.HARNESS_LINE,
        handle=harness,
        slot=str(branch),
        position=first,
        width=size[0],
        height=size[1],
        anchors=(Anchor(box=pad(span(first, second), TEXT_GAP), facing=facing),),
        own=(harness,),
    )


def text_centre(placed: PlacedText) -> Point:
    """HL16: a placed line text's centre, the record's `text_x`, `text_y`; always horizontal."""
    box = placed.box
    return Point(x=box.x + box.width // 2, y=box.y + box.height // 2)
