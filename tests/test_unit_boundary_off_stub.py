"""A unit's boundary connector wired by a top-level cable; a boundary connector declared unused draws no pin."""

from typing import Any

import fransys as fr
import fransys_parts
from _drawn_pages import drawn_pages
from _model_build_cover import cabinet_document, layout_trigger_document, unit_document
from fransys_author.design import Design

from fransys_model.vocab.tables import functions, ports

_PROJECT: dict[str, Any] = {
    "title": "Pump station",
    "number": "P-1001",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}


def _build():
    """A cabinet unit at +C1 whose boundary X1 is wired by the top-level cable W3 to +FLD;
    its second connector X2 is a boundary declared unused."""
    parts = fransys_parts.load("demo_parts")
    d = Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    u = d.scope("cab").unit("demo-pump-cabinet", revision=1, interface="1")
    u.revision(1, date="2026-01-01", text="First release", created="XX")
    c1 = u.location("C1", "Pump cabinet")
    grp = u.group("NET", "Network")
    x1 = u.item("DEMO-CONN-2P", tag="X1", at=c1, group=grp)
    x2 = u.item("DEMO-CONN-2P", tag="X2", at=c1, group=grp)
    u.boundary(x1)
    u.boundary(x2)
    u.unused(x2)
    fld, field = d.location("FLD", "Field"), d.group("NET", "Network")
    p2 = d.item("DEMO-CONN-2P", tag="P2", at=fld, group=field)
    cable = d.cable("DEMO-CBL-4G1.5", name="w3c", tag="W3", at=c1)
    cable.core(1, x1["1"], p2["1"])
    cable.core(2, x1["2"], p2["2"])
    return fr.build(parts, d.draft(), layout_trigger_document(), cabinet_document(fld), cabinet_document(c1), unit_document(u))


def test_a_boundary_declared_unused_draws_no_pin() -> None:
    result = _build()
    model = result.model
    x2 = {port for port, record in ports(model).items() if functions(model)[record.function].key[:2] == ("cab", "X2")}
    assert x2
    printed = {text.text for drawing in drawn_pages(model).values() for text in drawing.texts if text.kind == "TAG"}
    assert not {text for text in printed if text.startswith("-X2")}
