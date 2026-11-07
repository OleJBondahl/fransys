"""The invariants of a finished `Drawing`: no two things overlap, nothing leaves the page.

`OVERLAP`: two symbol bodies, a text and a body, two texts, a wire through a text, or a wire
across a body meet with positive area. `OUT_OF_PAGE`: a body, a text or a wire vertex lies outside
the content box or touches its edge (R746). `WIRE_OVER_MARKER`: a wire or a dot meets a reference marker's box.
`WIRE_NOT_ORTHOGONAL`: a wire has a diagonal segment. A unit frame is not
a body and a text is not part of an outline. Pure: reads `Drawing` values only. One finding per
member (a body pair, a wire and what it meets, a text).
"""

from itertools import combinations
from typing import TYPE_CHECKING

from fransys_layout.core import Box, inside, overlaps
from fransys_layout.drawing import page_texts, struck_texts, text_overlaps
lazy from fransys_model.kernel import Finding

from .codes import FINDING_CODES
from .drawn_geometry import crooked, dot_on_marker, dot_on_pin, over_markers, stray, through_bodies

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from fransys_layout.drawing import Drawing
    from fransys_model.kernel import Id
    from fransys_model.layout import Page

    from .drawn_netlist import Netlist, PagePart

__all__ = ["drawing_invariant_findings"]

XY = tuple[int, int]
_INFO = {info.code: info for info in FINDING_CODES}


def _at(box: Box) -> str:
    return f"({box.x}, {box.y})"


def _pairs(drawing: Drawing, ports: Mapping[str, XY]) -> Iterator[str]:
    """The key pair of each two symbol bodies that meet.

    A dot on a marker is `over_markers`'s; a dot on its symbol's own pin point is a connection.
    """
    held = [s for s in drawing.symbols if s.outline is not None]
    for a, b in combinations(held, 2):
        if not (a.outline and b.outline and overlaps(a.outline, b.outline)):
            continue
        if not dot_on_marker(a, b) and not dot_on_pin(a, b, ports):
            yield f"{a.key} / {b.key}"


def page_overlaps(drawing: Drawing, ports: Mapping[str, XY] | None = None) -> list[str]:
    """What meets what on one page: body pairs, then the texts' counts."""
    texts = page_texts(drawing)
    found = list(_pairs(drawing, ports or {}))
    found += [
        f"text at {_at(t.box)} / {s.key}"
        for t in texts
        for s in drawing.symbols
        if s.outline is not None and overlaps(t.box, s.outline) and not (getattr(t, "kind", "") == "SLOT" and getattr(t, "owner", "") == s.id)
    ]
    found += ["text / text"] * text_overlaps(texts)
    found += ["wire / text"] * struck_texts(drawing.wires, texts)
    return found


def outside(drawing: Drawing) -> list[str]:
    """What lies outside the content box of one page: bodies, then texts."""
    found = [s.key for s in drawing.symbols if s.outline and not inside(s.outline, drawing.area)]
    texts = [f"text at {_at(t.box)}" for t in page_texts(drawing) if not inside(t.box, drawing.area)]
    return found + texts


def _findings(code: str, page: Id[Page], members: list[str]) -> list[Finding]:
    """One finding per member, so a finding count is a member count; the message names the member."""
    return [_INFO[code].finding((page,), member) for member in members]


def _page_findings(page: Id[Page], part: PagePart) -> list[Finding]:
    drawing = part.drawing
    box = Box(0, 0, drawing.area.w, drawing.area.h)
    over = [*page_overlaps(drawing, part.ports), *through_bodies(part)]
    marked = over_markers(part)
    out = [*outside(drawing), *stray(part, box)]
    bent = crooked(part)
    return [
        *_findings("OVERLAP", page, over),
        *_findings("WIRE_OVER_MARKER", page, marked),
        *_findings("OUT_OF_PAGE", page, out),
        *_findings("WIRE_NOT_ORTHOGONAL", page, bent),
    ]


def drawing_invariant_findings(net: Netlist) -> tuple[Finding, ...]:
    """The four invariant codes for each page of `net` that has any."""
    return tuple(f for page, part in net.pages.items() for f in _page_findings(page, part))
