"""A wire run along three sides of one box reads as a second outline round it (layout-0176)."""

from itertools import pairwise
from typing import TYPE_CHECKING

from fransys_layout.geometry import WIRING_GRID, Box, Point, contains_point, meets

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable

    from .space import Shape

WRAP_GAP = 2 * WIRING_GRID  # how near a run is to a side to count as running along it
_SIDES = 3  # the number of sides that makes a wrap


def _sides_along(a: Point, b: Point, box: Box, gap: int) -> frozenset[str]:
    """Which sides of `box` the segment `a`-`b` runs along, within `gap` outside the side."""
    right, bottom = box.x + box.width, box.y + box.height
    if a.x == b.x:
        if not meets((min(a.y, b.y), max(a.y, b.y)), (box.y, bottom), closed=False):
            return frozenset[str]()
        near = {"left": box.x - gap <= a.x <= box.x, "right": right <= a.x <= right + gap}
    else:
        if not meets((min(a.x, b.x), max(a.x, b.x)), (box.x, right), closed=False):
            return frozenset[str]()
        near = {"top": box.y - gap <= a.y <= box.y, "bottom": bottom <= a.y <= bottom + gap}
    return frozenset(side for side, hit in near.items() if hit)


def _cap_strip(sides: frozenset[str], box: Box, room: Box) -> Box:
    """The strip from the side opposite the one side not run along, out to `room`'s edge."""
    missing = ({"left", "right", "top", "bottom"} - sides).pop()
    right, bottom = box.x + box.width, box.y + box.height
    strips = {
        "bottom": Box(x=box.x, y=room.y, width=box.width, height=max(box.y - room.y, 0)),
        "top": Box(
            x=box.x, y=bottom, width=box.width, height=max(room.y + room.height - bottom, 0)
        ),
        "right": Box(x=room.x, y=box.y, width=max(box.x - room.x, 0), height=box.height),
        "left": Box(x=right, y=box.y, width=max(room.x + room.width - right, 0), height=box.height),
    }
    return strips[missing]


def cap_strips(
    points: tuple[Point, ...], boxes: Iterable[Box], room: Box, gap: int = WRAP_GAP
) -> tuple[Box, ...]:
    """For each box `points` runs along exactly three sides of: the strip behind its cap side.

    A wire kept out of the strip cannot close the U over the box; `room` bounds the strip.
    """
    found = []
    for box in boxes:
        sides = frozenset().union(*(_sides_along(a, b, box, gap) for a, b in pairwise(points)))
        if len(sides) == _SIDES:
            found.append(_cap_strip(sides, box, room))
    return tuple(one for one in found if one.width and one.height)


def wrap_strips(
    points: tuple[Point, ...],
    shapes: Iterable[Shape],
    own: Collection[object],
    ends: Iterable[Point],
    room_gap: tuple[Box, int | None],
) -> tuple[Box, ...]:
    """The strips to block before `points` is searched again; none if the gap is None (off).

    Boxes of `own` owners are skipped, and so is a strip holding an end of the run.
    """
    room, gap = room_gap
    if gap is None:
        return ()
    boxes = [one.box for one in shapes if one.owner not in own and one.box.width and one.box.height]
    ends = tuple(ends)
    return tuple(
        strip
        for strip in cap_strips(points, boxes, room, gap)
        if not any(contains_point(strip, end.x, end.y) for end in ends)
    )
