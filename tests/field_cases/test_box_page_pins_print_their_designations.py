"""Field case: the pins of a connector on their device's box page print their designations.

The pins of a connector stand on the page of their device's box.

The engineering shape: one controller with a box (a system supply and a field supply) and an
8-pin connector function X1. X1 pins 1 to 4 are wired to one connector, pins 5 to 8 to another,
with `hide_unused_pins` on, in a cabinet schematic. The box and X1 pins 1 to 4 share a page;
pins 5 to 8 stand on the next one, and the page of the box has free room.

The bug: the pins on the box's page carry no designation, while the pins on the next page print
`-K4-X1:n`. A drawn pin always prints its designation. No finding says a label was lost.
The fix: layout-0131, a pin or connector designation names something below the item, so R4 keeps it.
"""

import tempfile
from pathlib import Path

import fransys as fr
from fransys.colours import BU

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_model.vocab.tables import functions, items, ports


def _layout():
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    d.layout.profile(hide_unused_pins=True)
    ctrl = d.device("K4", "DEMO-CTRL-8")
    first = d.device("J1", "DEMO-CONN-4P")
    second = d.device("Z1", "DEMO-CONN-4P")
    live = d.terminal_strip("X1", "DEMO-TB-2.5", 2).run("L", 2, bridged=True)
    zero = d.terminal_strip("X2", "DEMO-TB-2.5", 2).run("L", 2, bridged=True)
    d.dc_supply("S", plus=live[1], minus=zero[1], voltage=24)
    d.wire(ctrl.supply_system["S24V"], live[1].outer, wire=(BU, 0.5))
    d.wire(ctrl.supply_system["SGND"], zero[1].outer, wire=(BU, 0.5))
    d.wire(ctrl.supply_field["F24V1"], live[1].outer, wire=(BU, 0.5))
    d.wire(ctrl.supply_field["FGND1"], zero[1].outer, wire=(BU, 0.5))
    for k in range(1, 5):
        d.wire(first[str(k)], ctrl.X1[str(k)], wire=(BU, 0.5))
        d.wire(second[str(k)], ctrl.X1[str(k + 4)], wire=(BU, 0.5))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    model = fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)).model
    return model, stage_results(model, read_inputs(model))[0].layout


def test_every_drawn_pin_of_the_connector_has_its_tag():
    model, layout = _layout()
    (k4,) = (one.id for one in items(model).values() if one.tag == "K4")
    x1 = {f.id for f in functions(model).values() if f.item == k4 and f.name == "X1"}
    pin = {p.id: p.name for p in ports(model).values() if p.function in x1}
    drawn = {one.function: one.page for one in layout.placed if one.function in pin}
    assert sorted(pin[f] for f in drawn) == [str(n) for n in range(1, 9)]
    tagged = {one.subject: one.page for one in layout.labels if one.slot == "tag.pin"}
    missing = sorted(pin[f] for f, page in drawn.items() if tagged.get(f) != page)
    assert missing == []
