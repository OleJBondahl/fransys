"""Layout-0154: a harness line's drawn pieces on one page, as `write/` takes them."""

from itertools import pairwise
from typing import TYPE_CHECKING, Any

from fransys_layout.geometry import WIRING_GRID, Box, Facing, Point
from fransys_model.kernel import Id, value

if TYPE_CHECKING:
    from collections.abc import Sequence


@value
class DrawnLine:
    """One branch's polyline on one page; `text` is its designation's centre, `label` its box."""

    harness: Id[Any]
    branch: int
    drawing_set: int
    page: int
    points: tuple[Point, ...]
    text: Point
    label: Box


@value
class DrawnLeg:
    """One fan-out leg: the conductor it draws and its points, split first, pin last."""

    conductor: Id[Any]
    points: tuple[Point, ...]


@value
class DrawnFanOut:
    """One branch's fan-out on one page: its split point and one leg per conductor."""

    harness: Id[Any]
    branch: int
    drawing_set: int
    page: int
    at: Point
    legs: tuple[DrawnLeg, ...]


@value
class FarEnd:
    """One far end of a leaving line's stub: its port, and its page number and `x`, `y` there.

    `page` is the end's lowest page in the stub's drawing set, or `None` when it is drawn in
    none (STUB-POSITIONS P1, P2).
    """

    port: Id[Any]
    page: int | None
    x: int
    y: int


@value
class LineStub:
    """A leaving line's one stub (layout-0154): at the line's end, facing out, its text's box size.

    `port` is the near end's port and `far` the far end's, as an off stub names them.
    """

    harness: Id[Any]
    branch: int
    drawing_set: int
    page: int
    port: Id[Any]
    far: Id[Any]
    at: Point
    facing: Facing
    box: Box
    ends: tuple[FarEnd, ...] = ()


def slant_boxes(points: Sequence[Point]) -> list[Box]:
    """Boxes along a polyline, one per half grid of each segment, so a slant's boxes stay thin."""
    boxes: list[Box] = []
    for one, two in pairwise(points):
        n = max(abs(two.x - one.x), abs(two.y - one.y)) // (WIRING_GRID // 2) or 1
        at = [
            Point(x=one.x + (two.x - one.x) * i // n, y=one.y + (two.y - one.y) * i // n)
            for i in range(n + 1)
        ]
        boxes += [
            Box(x=min(a.x, b.x), y=min(a.y, b.y), width=abs(a.x - b.x), height=abs(a.y - b.y))
            for a, b in pairwise(at)
        ]
    return boxes
