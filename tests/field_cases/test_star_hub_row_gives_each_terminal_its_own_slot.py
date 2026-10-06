"""Field case: a unit's earth hub wired to two terminals, whose boundary pins stand in a row.

The shape: inside a unit one earth hub terminal is wired to two others (`left` and `right`). In the
parent's drawing set the same four terminals stand as boundary pins in one row of one group: left,
hub, an unwired pin, right. The hub is beside `left` only there, so the net is a star and both
terminals that stand above the hub attach to the hub's one port.

The bug (v0.11.0): both attachments were put at the host port's x, so `left` and `right` shared one
spot (identical 16x16 keep-out boxes, `SYMBOL_OVERLAP`). The second takes the row's next free slot,
the gap any neighbour in a row gets (R7.1, layout-0122, an existing rule).
"""

from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
from _model_build_cover import system_document

from fransys_model.layout import SymbolPlacement, layout_of

_PROJECT: dict[str, Any] = {
    "title": "Star hub row",
    "number": "P-1",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}


def _built() -> fr.BuildResult:
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    cab = d.scope("cab").unit("demo-pump-cabinet", revision=1, interface="1")
    cab.revision(1, date="2026-01-01", text="First release", created="XX")
    c1 = cab.location("C1", "Cabinet")
    g1 = cab.group("G1", "Group 1")
    x1, x2, x3 = (cab.strip(name, at=c1) for name in ("X1", "X2", "X3"))
    left, hub = (x1.terminal("DEMO-TB-2.5", group=g1) for _ in range(2))
    filler = x2.terminal("DEMO-TB-2.5", group=g1)
    right = x3.terminal("DEMO-TB-2.5", group=g1)
    earth = cab.wiring(colour="GNYE", gauge="2.5")
    earth(hub.inner, left.inner)
    earth(hub.inner, right.inner)
    for terminal in (left, hub, filler, right):
        cab.boundary(terminal)
    return fr.build(parts, d.draft(), system_document())


def test_two_terminals_above_one_hub_stand_apart() -> None:
    result = _built()
    placements = layout_of(result.model, SymbolPlacement).values()
    spots = [(p.page, p.x, p.y) for p in placements]
    assert len(spots) >= 4  # the layout ran
    assert len(spots) == len(set(spots))
    assert "SYMBOL_OVERLAP" not in {f.code for f in result.findings}
