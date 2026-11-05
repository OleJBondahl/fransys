"""A rack's child order is authored, so layout
follows it. The modules stand in `position` order, each with its own columns, whatever
their keys or designations say.
"""

from typing import Any

import fransys as fr
import fransys_parts
from _drawn_pages import drawn_pages
from _model_build_cover import cabinet_document
from fransys_author.design import Design

_PROJECT: dict[str, Any] = {
    "title": "Rack order",
    "number": "P-1002",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}


def test_a_racks_modules_stand_in_their_authored_position_order() -> None:
    parts = fransys_parts.load("demo_parts")
    d = Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    c1, plc = d.location("C1", "Cabinet"), d.group("PLC", "PLC")
    rack = d.item(None, tag="U1", at=c1, group=plc)
    do = d.item("DEMO-PLC-DO-2", tag="DO1", name="do", parent=rack, position=1, at=c1, group=plc)
    di = d.item("DEMO-PLC-DI-2", tag="DI1", name="di", parent=rack, position=2, at=c1, group=plc)
    k1 = d.item("DEMO-RLY-2CO-24", tag="K1", at=c1, group=plc)
    k2 = d.item("DEMO-RLY-2CO-24", tag="K2", at=c1, group=plc)
    wire = d.wiring(colour="BU", gauge="0.5")
    wire(do.fn("do_1")["1"], k1.fn("coil")["A1"])
    wire(di.fn("di_1")["1"], k2.fn("co_1")["14"])
    strip = d.strip("X1", at=c1)
    for port in (k1.fn("coil")["A2"], k2.fn("co_1")["11"], k2.fn("co_1")["12"]):
        wire(port, strip.terminal("DEMO-TB-2.5", group=plc).inner)
    model = fr.build(parts, d.draft(), cabinet_document(c1)).model
    x = {}
    for drawing in drawn_pages(model).values():
        for symbol in drawing.symbols:
            for name, _ in symbol.slots:
                module = name.removeprefix("marking.").split("_")[0]
                if symbol.key == "generic-box" and module in {"do", "di"}:
                    x[(module,)] = symbol.x
    assert x[("do",)] < x[("di",)]
