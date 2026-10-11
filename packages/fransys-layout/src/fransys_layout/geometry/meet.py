"""Where two extents meet: one closed or open test for spans, boxes and points.

Closed means an edge or a corner is enough (`<=`), open means shared interior (`<`). There is no
emptiness guard here: `boxes_meet` of a zero-size box answers by the comparisons alone, and a site
that needs the guard (`overlaps`) keeps it.
"""

from typing import TYPE_CHECKING

from .boxes import Box, pad

if TYPE_CHECKING:
    from .units import Point

type Span = tuple[int, int]


def meets(
    a: Span, b: Span, *, closed: bool = True, open_a: tuple[bool, bool] = (False, False)
) -> bool:
    """Whether span `a` meets span `b`; `open_a` leaves one end of `a` out of a closed test."""
    low_strict = not closed or open_a[0]
    high_strict = not closed or open_a[1]
    return (b[1] > a[0] if low_strict else b[1] >= a[0]) and (
        b[0] < a[1] if high_strict else b[0] <= a[1]
    )


def boxes_meet(a: Box, b: Box, *, closed: bool, gap: int = 0) -> bool:
    """Whether `a`, grown by `gap` on every side, meets `b` on both axes."""
    grown = pad(a, gap) if gap else a
    return meets((grown.x, grown.x + grown.width), (b.x, b.x + b.width), closed=closed) and meets(
        (grown.y, grown.y + grown.height), (b.y, b.y + b.height), closed=closed
    )


def contains_point(box: Box, x: int, y: int) -> bool:
    """Whether the point `(x, y)` is in `box`, edges included."""
    return box.x <= x <= box.x + box.width and box.y <= y <= box.y + box.height


def through(segment: tuple[Point, Point], box: Box) -> bool:
    """Whether `segment` passes through `box`'s interior; touching an edge does not count."""
    (a, b), low, high = segment, 0.0, 1.0
    for start, delta, lo, hi in (
        (a.x, b.x - a.x, box.x, box.x + box.width),
        (a.y, b.y - a.y, box.y, box.y + box.height),
    ):
        if delta == 0:
            if not lo < start < hi:
                return False
            continue
        one, two = (lo - start) / delta, (hi - start) / delta
        low, high = max(low, min(one, two)), min(high, max(one, two))
    return low < high
