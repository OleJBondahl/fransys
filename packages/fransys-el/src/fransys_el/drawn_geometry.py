"""What a finished page's wires do against the page and the bodies (DRAWN-NETLIST, el-0052).

`crooked`: a wire with a segment that is neither horizontal nor vertical. `stray`: a wire vertex
outside the content box. `through_bodies`: a wire runs across a symbol body it does not end at.
`over_markers`: a wire or a junction dot meets the box of a reference marker (MARKER-FREE-SIDE).
Pure: reads a `PagePart`.
"""

from itertools import pairwise
from typing import TYPE_CHECKING

from fransys_layout.core import overlaps, own_end, through

from .drawn_netlist import is_marker

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

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


def _in(p: XY, box: Box) -> bool:
    return box.x <= p[0] <= box.x + box.w and box.y <= p[1] <= box.y + box.h


def _runs(points: Sequence[XY], box: Box, ports: Sequence[XY]) -> bool:
    """True when a run of the wire `points` passes `box` (`core.through`), the wire's ends and the owner's `ports` being its pins."""
    return any(through(a, b, box, (points[0], points[-1]), ports) for a, b in pairwise(points))


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
            if not any(own_end(q, e) for q in ports for e in (w.points[0], w.points[-1])) and _runs(w.points, box, ports)
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


def _without_port_end(points: Sequence[XY], ports: Sequence[XY]) -> tuple[Sequence[XY], Sequence[XY]]:
    """The wire's points less an end point at one of `ports`, and those less the far point of that entry segment too.

    The first is the run the wire keeps; the second the points that may lie in a box: the entry segment is exempt whole (R2101).
    """
    kept, free = points, points
    if any(own_end(q, kept[-1]) for q in ports):
        kept, free = kept[:-1], free[:-2]
    if kept and any(own_end(q, kept[0]) for q in ports):
        kept, free = kept[1:], free[1:]
    return kept, free


def _meets_box(points: Sequence[XY], box: Box, ports: Sequence[XY]) -> bool:
    kept, free = _without_port_end(points, ports)
    return any(_in(p, box) for p in free) or _runs(kept, box, ports)


def over_markers(part: PagePart) -> list[str]:
    """One member per (wire or dot, marker): `wire / <key>` or `dot / <key>`, in drawing order.

    A wire with a point in the marker's box (its edge included) or crossing it counts. Only the end
    segment that enters the marker's own port is exempt, so a wire that runs on through the box counts (R2062).
    """
    found: list[str] = []
    for marker in part.drawing.symbols:
        box = marker.outline
        if box is None or not is_marker(marker):
            continue
        ports = [(marker.x, marker.y), *(part.ports[p] for p in marker.ports if p in part.ports)]
        found += [f"wire / {marker.key}" for w in part.drawing.wires if _meets_box(w.points, box, ports)]
        found += [f"dot / {marker.key}" for d in part.drawing.symbols if dot_on_marker(d, marker) and not any(own_end(q, (d.x, d.y)) for q in ports)]
    return found
