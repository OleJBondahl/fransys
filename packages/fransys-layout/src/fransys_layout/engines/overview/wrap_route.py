"""The fold route of a wrapped sheet: a line leaving one row's end for the next row's start.

A general technique over plain points: the route runs out to the right of a row, down to a track
between two rows, back to the left of the next row and down to the line's end. `clear` says whether
a set of routes touches a box or crosses a line.
"""

from itertools import pairwise
lazy from collections.abc import Iterable, Sequence

from fransys_layout.geometry import Point
lazy from fransys_layout.engines.overview.sheet_values import PlacedBox

type Segment = tuple[Point, Point]


def fold_points(
    first: Point, last: Point, *, right: int, left: int, track: int
) -> tuple[Point, ...]:
    """`first` out to `right`, down to `track`, back to `left`, down to `last`'s row and in."""
    return (
        first,
        Point(x=right, y=first.y),
        Point(x=right, y=track),
        Point(x=left, y=track),
        Point(x=left, y=last.y),
        last,
    )


def segments(points: Sequence[Point]) -> list[Segment]:
    """The runs of a line, each a pair of points."""
    return list(pairwise(points))


def _hits(seg: Segment, box: PlacedBox) -> bool:
    """Whether the run enters the box's inside (touching its edge is no hit)."""
    (x0, y0), (x1, y1) = ((p.x, p.y) for p in seg)
    return (
        min(x0, x1) < box.x + box.width
        and max(x0, x1) > box.x
        and min(y0, y1) < box.y + box.height
        and max(y0, y1) > box.y
    )


def _crosses(one: Segment, other: Segment) -> bool:
    """Whether a horizontal and a vertical run cross inside both; parallel runs never do."""
    (a, b), (c, d) = one, other
    if a.y == b.y and c.x == d.x:
        return min(a.x, b.x) < c.x < max(a.x, b.x) and min(c.y, d.y) < a.y < max(c.y, d.y)
    if a.x == b.x and c.y == d.y:
        return _crosses(other, one)
    return False


def clear(
    routes: Iterable[Sequence[Point]], boxes: Sequence[PlacedBox], lines: Iterable[Sequence[Point]]
) -> bool:
    """Whether no route touches a box's inside or crosses a run of `lines` (the routes included)."""
    runs = [segments(p) for p in lines]
    for route in routes:
        for seg in segments(route):
            if any(_hits(seg, b) for b in boxes):
                return False
            if any(_crosses(seg, o) for rs in runs for o in rs if o != seg):
                return False
    return True
