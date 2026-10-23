"""What a finished page's wires do against the page and the bodies (DRAWN-NETLIST, el-0052).

`crooked`: a wire with a segment that is neither horizontal nor vertical. `stray`: a wire vertex
outside the content box. `through_bodies`: a wire runs across a symbol body it does not end at.
Pure: reads a `PagePart`.
"""

from itertools import pairwise
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fransys_layout.core import Box

    from .drawn_netlist import PagePart

__all__ = ["crooked", "stray", "through_bodies"]

XY = tuple[int, int]


def crooked(part: PagePart) -> list[str]:
    """One member per wire with a diagonal segment, named by its first point."""
    return [
        f"wire at {w.points[0]}"
        for w in part.drawing.wires
        if any(a[0] != b[0] and a[1] != b[1] for a, b in pairwise(w.points))
    ]


def stray(part: PagePart, page: Box) -> list[str]:
    """One member per wire vertex outside `page` (the content box)."""
    return [
        f"wire vertex {p}"
        for w in part.drawing.wires
        for p in w.points
        if not (page.x <= p[0] <= page.x + page.w and page.y <= p[1] <= page.y + page.h)
    ]


def _crosses(a: XY, b: XY, box: Box) -> bool:
    """True when the rectilinear segment a-b runs a positive length inside `box`'s interior."""
    (x1, y1), (x2, y2) = a, b
    if x1 == x2:
        return box.x < x1 < box.x + box.w and min(y1, y2) < box.y + box.h and max(y1, y2) > box.y
    return box.y < y1 < box.y + box.h and min(x1, x2) < box.x + box.w and max(x1, x2) > box.x


def _in(p: XY, box: Box) -> bool:
    return box.x <= p[0] <= box.x + box.w and box.y <= p[1] <= box.y + box.h


def through_bodies(part: PagePart) -> list[str]:
    """One member per (wire, body) where the wire crosses a body and ends in none of its box."""
    found: list[str] = []
    for symbol in part.drawing.symbols:
        if symbol.outline is None or symbol.key == "junction-dot":
            continue
        own = {(symbol.x, symbol.y), *(part.ports[p] for p in symbol.ports if p in part.ports)}
        found += [
            f"wire / {symbol.key}"
            for w in part.drawing.wires
            if w.points[0] not in own
            and w.points[-1] not in own
            and not _in(w.points[0], symbol.outline)
            and not _in(w.points[-1], symbol.outline)
            and any(_crosses(a, b, symbol.outline) for a, b in pairwise(w.points))
        ]
    return found
