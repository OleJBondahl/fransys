"""What a finished page's wires do against the page and the bodies (DRAWN-NETLIST, el-0052).

`crooked`: a wire with a segment that is neither horizontal nor vertical. `stray`: a wire vertex
outside the content box. `through_bodies`: a wire runs across a symbol body it does not end at.
`over_markers`: a wire or a junction dot meets the box of a reference marker (MARKER-FREE-SIDE).
Pure: reads a `PagePart`.
"""

from itertools import pairwise
from typing import TYPE_CHECKING

from fransys_layout.core import overlaps, own_end

from .drawn_netlist import is_marker

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.core import Box
    from fransys_layout.drawing import DrawnSymbol

    from .drawn_netlist import PagePart

__all__ = ["crooked", "dot_on_marker", "dot_on_pin", "over_markers", "stray", "through_bodies"]

XY = tuple[int, int]


def crooked(part: PagePart) -> list[str]:
    """One member per wire with a diagonal segment, named by its first point."""
    return [f"wire at {w.points[0]}" for w in part.drawing.wires if any(a[0] != b[0] and a[1] != b[1] for a, b in pairwise(w.points))]


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
    """One member per (wire, box) sharing interior where the wire ends at none of the box's own ports.

    A wire may end inside a box only at its own pin; a table head counts too (R1055, R1058). A marker is `over_markers`'s.
    """
    found: list[str] = []
    for symbol in part.drawing.symbols:
        if symbol.outline is None or symbol.key == "junction-dot" or is_marker(symbol):
            continue
        box = symbol.outline
        ports = [(symbol.x, symbol.y), *(part.ports[p] for p in symbol.ports if p in part.ports)]
        found += [
            f"wire / {symbol.key}"
            for w in part.drawing.wires
            if not any(own_end(q, e) for q in ports for e in (w.points[0], w.points[-1])) and any(_crosses(a, b, box) for a, b in pairwise(w.points))
        ]
    return found


def dot_on_marker(a: DrawnSymbol, b: DrawnSymbol) -> bool:
    """True when one is a junction dot and the other a marker whose box holds or meets it."""
    dot, mark = (a, b) if a.key == "junction-dot" else (b, a)
    box = mark.outline
    if dot.key != "junction-dot" or box is None or not is_marker(mark):
        return False
    return _in((dot.x, dot.y), box) or (dot.outline is not None and overlaps(dot.outline, box))


def dot_on_pin(a: DrawnSymbol, b: DrawnSymbol, ports: Mapping[str, XY]) -> bool:
    """True when one is a junction dot centred on a pin point of the other (its own net's)."""
    dot, body = (a, b) if a.key == "junction-dot" else (b, a)
    if dot.key != "junction-dot" or body.key == "junction-dot":
        return False
    return (dot.x, dot.y) in {ports[p] for p in body.ports if p in ports}


def over_markers(part: PagePart) -> list[str]:
    """One member per (wire or dot, marker): `wire / <key>` or `dot / <key>`, in drawing order.

    A wire with a point in the marker's box (its edge included) or crossing it counts; a wire
    ending at the marker's own port does not, since the stub's wire ends there.
    """
    found: list[str] = []
    for marker in part.drawing.symbols:
        box = marker.outline
        if box is None or not is_marker(marker):
            continue
        ports = [(marker.x, marker.y), *(part.ports[p] for p in marker.ports if p in part.ports)]
        found += [
            f"wire / {marker.key}"
            for w in part.drawing.wires
            if not any(own_end(q, e) for q in ports for e in (w.points[0], w.points[-1]))
            and (any(_in(p, box) for p in w.points) or any(_crosses(a, b, box) for a, b in pairwise(w.points)))
        ]
        found += [f"dot / {marker.key}" for d in part.drawing.symbols if dot_on_marker(d, marker) and not any(own_end(q, (d.x, d.y)) for q in ports)]
    return found
