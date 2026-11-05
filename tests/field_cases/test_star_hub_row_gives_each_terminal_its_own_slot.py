"""Field case: a unit's earth hub wired to two terminals that stand as boundary pins in one row above the hub.
The bug (v0.11.0): both attachments were put at the host port's x, so `left` and `right` shared one spot and raised SYMBOL_OVERLAP.
Fixed by layout-0122, the second attachment takes the row's next free slot, the gap any neighbour in a row gets."""

from typing import Any

import fransys as fr
import fransys_parts
from _drawn_pages import drawn_pages
from _model_build_cover import cabinet_document, unit_document
from fransys_author.design import Design

_PROJECT: dict[str, Any] = {
    "title": "Star hub row",
    "number": "P-1",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}


def _built() -> fr.BuildResult:
    parts = fransys_parts.load("demo_parts")
    d = Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    cab = d.scope("cab").unit("demo-pump-cabinet", revision=1, interface="1")
    cab.revision(1, date="2026-01-01", text="First release", created="XX")
    c1 = cab.location("C1", "Cabinet")
    g1 = cab.group("G1", "Group 1")
    x1, x2, x3 = (cab.strip(name, at=c1) for name in ("X1", "X2", "X3"))
    left = x1.terminal("DEMO-TB-2.5", group=g1)
    hub = x1.terminal("DEMO-TB-2.5-TWIN", group=g1)
    filler = x2.terminal("DEMO-TB-2.5", group=g1)
    right = x3.terminal("DEMO-TB-2.5", group=g1)
    earth = cab.wiring(colour="GNYE", gauge="2.5")
    earth(hub.inner, left.inner)
    earth(hub.inner, right.inner)
    for terminal in (left, hub, filler, right):
        cab.boundary(terminal)
    return fr.build(parts, d.draft(), cabinet_document(c1), unit_document("demo-pump-cabinet"))


def test_two_terminals_above_one_hub_stand_apart() -> None:
    result = _built()
    pages = drawn_pages(result.model)
    spots = [(page, s.x, s.y) for page, drawing in pages.items() for s in drawing.symbols]
    assert len(spots) >= 4  # the layout ran
    assert len(spots) == len(set(spots))
    assert "SYMBOL_OVERLAP" not in {f.code for f in result.findings}
