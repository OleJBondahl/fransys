"""The invariants of a finished `Drawing`: no two things overlap, nothing leaves the page.

`OVERLAP`: two symbol bodies, a text and a body, two texts, a wire through a text, or a wire
across a body meet with positive area. `OUT_OF_PAGE`: a body, a text or a wire vertex lies outside
the content box. `WIRE_NOT_ORTHOGONAL`: a wire has a diagonal segment. A unit frame is not
a body and a text is not part of an outline. Pure: reads `Drawing` values only. One finding per
code and page, naming up to `_NAMED` of its members.
"""

from itertools import combinations
from typing import TYPE_CHECKING

from fransys_layout.core import Box, overlaps
from fransys_layout.drawing import page_texts, struck_texts, text_overlaps
from fransys_model.kernel import Finding

from .codes import FINDING_CODES
from .drawn_geometry import crooked, stray, through_bodies

if TYPE_CHECKING:
    from collections.abc import Iterator

    from fransys_layout.drawing import Drawing
    from fransys_model.kernel import Id
    from fransys_model.layout import Page

    from .drawn_netlist import Netlist, PagePart

__all__ = ["drawing_invariant_findings"]

_NAMED = 3
_INFO = {info.code: info for info in FINDING_CODES}


def _at(box: Box) -> str:
    return f"({box.x}, {box.y})"


def _span(lo: int, size: int, outer_lo: int, outer_size: int) -> bool:
    return outer_lo <= lo and lo + size <= outer_lo + outer_size


def _inside(box: Box, page: Box) -> bool:
    return _span(box.x, box.w, page.x, page.w) and _span(box.y, box.h, page.y, page.h)


def _pairs(drawing: Drawing) -> Iterator[str]:
    """The key pair of each two symbol bodies that meet."""
    held = [(s.key, s.outline) for s in drawing.symbols if s.outline is not None]
    for (ka, oa), (kb, ob) in combinations(held, 2):
        if overlaps(oa, ob):
            yield f"{ka} / {kb}"


def page_overlaps(drawing: Drawing) -> list[str]:
    """What meets what on one page: body pairs, then the texts' counts."""
    texts = page_texts(drawing)
    found = list(_pairs(drawing))
    found += [
        f"text at {_at(t.box)} / {s.key}"
        for t in texts
        for s in drawing.symbols
        if s.outline is not None and overlaps(t.box, s.outline)
    ]
    found += ["text / text"] * text_overlaps(texts)
    found += ["wire / text"] * struck_texts(drawing.wires, texts)
    return found


def outside(drawing: Drawing) -> list[str]:
    """What lies outside the content box of one page: bodies, then texts."""
    page = Box(0, 0, drawing.area.w, drawing.area.h)
    found = [s.key for s in drawing.symbols if s.outline and not _inside(s.outline, page)]
    texts = [f"text at {_at(t.box)}" for t in page_texts(drawing) if not _inside(t.box, page)]
    return found + texts


def _finding(code: str, page: Id[Page], members: list[str]) -> Finding:
    named = ", ".join(members[:_NAMED])
    more = f" and {len(members) - _NAMED} more" if len(members) > _NAMED else ""
    return Finding(
        code=code,
        severity=_INFO[code].severities[0],
        subjects=(page,),
        message=f"{len(members)} on one page: {named}{more}",
        fix=_INFO[code].filled(),
    )


def _page_findings(page: Id[Page], part: PagePart) -> list[Finding]:
    drawing = part.drawing
    box = Box(0, 0, drawing.area.w, drawing.area.h)
    over = [*page_overlaps(drawing), *through_bodies(part)]
    out = [*outside(drawing), *stray(part, box)]
    bent = crooked(part)
    return [
        *([_finding("OVERLAP", page, over)] if over else []),
        *([_finding("OUT_OF_PAGE", page, out)] if out else []),
        *([_finding("WIRE_NOT_ORTHOGONAL", page, bent)] if bent else []),
    ]


def drawing_invariant_findings(net: Netlist) -> tuple[Finding, ...]:
    """OVERLAP, OUT_OF_PAGE and WIRE_NOT_ORTHOGONAL for each page of `net` that has any."""
    return tuple(f for page, part in net.pages.items() for f in _page_findings(page, part))
