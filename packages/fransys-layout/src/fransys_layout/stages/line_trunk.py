"""TALL-PAGE R1 (layout-0167): where a line whose root is on another page leaves its bar.

The trunk runs `LEAVE_GRIDS` straight out of a free point of the bar near its middle, the way the
line enters the root's box, and ends in its stub. The stub's box is measured from `size`.
"""

from itertools import pairwise
from typing import TYPE_CHECKING

from fransys_layout.geometry import WIRING_GRID, Box, Facing, Point, boxes_meet, port_exit

from .space import End, span
from .texts.candidates import Candidate, box_of, stub_anchor

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from .harness_route import Grid

LEAVE_GRIDS = 6  # HL18: a leaving line runs 48 G, one column gap, straight out


def tip(end: End) -> End:
    """Where a leaving line ends and its stub starts, facing on out (HL18)."""
    return End(at=port_exit(end.at, end.facing, LEAVE_GRIDS), facing=end.facing)


def edge(end: End) -> Point:
    """Where a leaving line meets its stub's box: its near edge's middle, as `stub_box` has it."""
    found = box_of(Candidate(side=end.facing, offset=0), stub_anchor(tip(end).at), (0, 0))
    return Point(x=found.x, y=found.y)


def trunk_end(
    bar: Mapping[int, tuple[Point, ...]], grid: Grid, entry: Facing, size: tuple[int, int]
) -> End | None:
    """The free point of `bar` nearest its middle, left first on a tie, facing `entry`.

    Free: the run to the stub and the stub's box cross no keep-out and no run of the bar, and
    stand inside the region. `None` when no point is free.
    """
    runs = [one for points in bar.values() for one in pairwise(points)]
    points = [point for points in bar.values() for point in points]
    middle = Point(
        x=(min(p.x for p in points) + max(p.x for p in points)) // 2,
        y=(min(p.y for p in points) + max(p.y for p in points)) // 2,
    )
    on_bar = frozenset(at for one in runs for at in _grid_points(*one))
    for at in sorted(on_bar, key=lambda p: (abs(p.x - middle.x) + abs(p.y - middle.y), p.x, p.y)):
        end = End(at=at, facing=entry)
        if _free(end, on_bar, grid, size):
            return end
    return None


def _grid_points(first: Point, second: Point) -> list[Point]:
    """The points a straight run passes, one wiring grid apart, both ends included."""
    count = max(abs(second.x - first.x), abs(second.y - first.y)) // WIRING_GRID
    step_x = (second.x > first.x) - (second.x < first.x)
    step_y = (second.y > first.y) - (second.y < first.y)
    return [
        Point(x=first.x + step_x * WIRING_GRID * n, y=first.y + step_y * WIRING_GRID * n)
        for n in range(count + 1)
    ]


def _free(end: End, bar: frozenset[Point], grid: Grid, size: tuple[int, int]) -> bool:
    out = edge(end)
    run = span(end.at, out)
    box = box_of(Candidate(side=end.facing, offset=0), stub_anchor(tip(end).at), size)
    ahead = {at for at in _grid_points(end.at, out) if at != end.at}
    region = grid.region
    inside = (
        region.x <= box.x
        and region.y <= box.y
        and box.x + box.width <= region.x + region.width
        and box.y + box.height <= region.y + region.height
    )
    return (
        inside
        and not ahead & bar
        and not any(_meets(one.box, (run, box)) for one in grid.obstacles)
    )


def _meets(shape: Box, boxes: Iterable[Box]) -> bool:
    return any(boxes_meet(shape, one, closed=True) for one in boxes)


def halves(points: tuple[Point, ...], at: Point) -> tuple[tuple[Point, ...], tuple[Point, ...]]:
    """`points` cut at `at`: the run from its first end to `at`, and from its last end to `at`.

    The bar of two ends is one polyline; each end's branch draws its own half of it.
    """
    for n, (one, other) in enumerate(pairwise(points)):
        if one == at or span(one, other).x <= at.x <= span(one, other).x + span(one, other).width:
            box = span(one, other)
            if box.y <= at.y <= box.y + box.height:
                head = (*points[: n + 1], at)
                tail = (*reversed(points[n + 1 :]), at)
                return _clean(head), _clean(tail)
    return points, tuple(reversed(points))


def _clean(points: Sequence[Point]) -> tuple[Point, ...]:
    """`points` less a repeat of a point next to itself."""
    return tuple(p for n, p in enumerate(points) if n == 0 or p != points[n - 1])
