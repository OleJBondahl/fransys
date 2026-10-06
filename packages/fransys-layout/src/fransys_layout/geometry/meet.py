"""Where two extents meet: one closed or open test for spans, boxes and points (cleanup step 2, F1).

Closed means an edge or a corner is enough (`<=`), open means shared interior (`<`). There is no
emptiness guard here: `boxes_meet` of a zero-size box answers by the comparisons alone, and a site
that needs the guard (`overlaps`) keeps it.
"""

from .boxes import Box, pad

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
