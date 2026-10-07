"""W3 (layout deep dive, designer's ruling): a unit's boundary connector mated to the plug of
a top-level harness shows, in the unit's own set, its pins with the harness's off-stub, as
the terminals of a top-level cable do; a boundary connector declared unused draws no pin.

Can-fail, checked by hand: without `_boundary_offs` in `read_inputs` the cabinet's X1 pins
carry no off-stub and the first test fails; with unused boundaries kept in
`_without_idle_pins` the X2 pins are drawn and the second fails.
"""

from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
from _model_build_cover import layout_trigger_document

from fransys_model.derive.drawing_text import off_stub_text
from fransys_model.layout import (
    DrawingSet,
    LinkMarker,
    Page,
    StarKind,
    SymbolPlacement,
    layout_of,
)
from fransys_model.vocab.tables import functions, ports

_PROJECT: dict[str, Any] = {
    "title": "Pump station",
    "number": "P-1001",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}


def _build():
    """A cabinet unit at +C1 whose boundary X1 mates the +C1 plug of the top-level harness
    W3, running to +FLD; its second connector X2 is a boundary declared unused."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
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
    w3 = d.harness(name="w3", tag="W3", at=c1, group=field)
    p1 = d.item("DEMO-CONN-2P", tag="P1", parent=w3, at=c1, group=field)
    p2 = d.item("DEMO-CONN-2P", tag="P2", parent=w3, at=fld, group=field)
    cable = d.cable("DEMO-CBL-4G1.5", name="w3c", parent=w3, at=c1)
    cable.core(1, p1["1"], p2["1"])
    cable.core(2, p1["2"], p2["2"])
    d.mate(p1, x1)
    return fr.build(parts, d.draft(), layout_trigger_document())


def _in_cabinet_set(model, page):
    drawing_set = layout_of(model, DrawingSet)[layout_of(model, Page)[page].drawing_set]
    return drawing_set.unit is not None


def _owner(model, port):
    return functions(model)[ports(model)[port].function]


def test_the_units_boundary_pins_carry_the_top_level_harnesss_off_stub() -> None:
    result = _build()
    model = result.model
    stubs = [
        m
        for m in layout_of(model, LinkMarker).values()
        if m.star is StarKind.OFF and _in_cabinet_set(model, m.page)
    ]
    assert {ports(model)[m.port].name for m in stubs} == {"1", "2"}
    assert {_owner(model, m.port).key[:2] for m in stubs} == {("cab", "X1")}
    texts = {off_stub_text(model, m) for m in stubs}
    assert all(text.startswith("-W3") and "+FLD" in text for text in texts)
    # the X1 pins stand in a column, not alone ("in no chain"); only the far plug P2 does
    lone = {
        s for f in result.findings if f.code == "FUNCTION_UNPLACED_IN_COLUMN" for s in f.subjects
    }
    assert not lone & {m.port for m in stubs}


def test_a_boundary_declared_unused_draws_no_pin() -> None:
    result = _build()
    model = result.model
    x2 = {
        port
        for port, record in ports(model).items()
        if functions(model)[record.function].key[:2] == ("cab", "X2")
    }
    placed = {p.function for p in layout_of(model, SymbolPlacement).values()}
    assert x2
    assert not placed & (x2 | {ports(model)[p].function for p in x2})
    assert "UNIT_CONNECTOR_DANGLING" not in {f.code for f in result.findings}
