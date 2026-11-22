"""Where two extents meet: one closed or open test for spans, boxes and points.

Closed means an edge or a corner is enough (`<=`), open means shared interior (`<`). There is no
emptiness guard here; a site that needs one (`overlaps`) keeps it.
"""

lazy from .boxes import Box

type Span = tuple[int, int]


def meets(a: Span, b: Span, *, closed: bool = True, open_a: tuple[bool, bool] = (False, False)) -> bool:
    """Whether span `a` meets span `b`; `open_a` leaves one end of `a` out of a closed test."""
    low_strict = not closed or open_a[0]
    high_strict = not closed or open_a[1]
    return (b[1] > a[0] if low_strict else b[1] >= a[0]) and (b[0] < a[1] if high_strict else b[0] <= a[1])


def contains_point(box: Box, x: int, y: int) -> bool:
    """Whether the point `(x, y)` is in `box`, edges included."""
    return box.x <= x <= box.x + box.width and box.y <= y <= box.y + box.height
