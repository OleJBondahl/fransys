"""F1 (layout deep dive, designer's ruling): a rack's child order is authored, so layout
follows it. The modules stand in `position` order, each with its own columns, whatever
their keys or designations say.

Can-fail, checked by hand: without `rack_order` the DI module (key "di" before "do") stands
left of the DO module and the test fails.
"""

from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
from _model_build_cover import layout_trigger_document

from fransys_model.layout import SymbolPlacement, layout_of
from fransys_model.vocab.tables import functions, items

_PROJECT: dict[str, Any] = {
    "title": "Rack order",
    "number": "P-1002",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}


def test_a_racks_modules_stand_in_their_authored_position_order() -> None:
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
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
    model = fr.build(parts, d.draft(), layout_trigger_document()).model
    item_key = {record.id: record.key for record in items(model).values()}
    x = {}
    for placement in layout_of(model, SymbolPlacement).values():
        function = functions(model).get(placement.function)
        if function is not None and item_key[function.item] in {("do",), ("di",)}:
            x[item_key[function.item]] = placement.x
    assert x[("do",)] < x[("di",)]
