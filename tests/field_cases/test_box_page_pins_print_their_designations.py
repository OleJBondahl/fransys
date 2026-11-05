"""Field case: a controller box and an 8-pin connector X1 in a cabinet schematic, with pins 1 to 4 on the box's page and 5 to 8 on the next.
The bug: the pins on the box's page carried no designation while the pins on the next page printed `-K4-X1:n`, and no finding said so.
Fixed by layout-0131, a pin or connector designation names something below the item, so R4 keeps it."""

import fransys as fr
from _drawn_facts import symbol_subjects
from _drawn_pages import drawn_pages
from _model_build_cover import unit_document
from fransys.colours import BU

from fransys_model.derive import port_designation
from fransys_model.vocab.tables import functions, items, ports


def _layout():
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    d.layout.profile(hide_unused_pins=True)
    ctrl = d.device("K4", "DEMO-CTRL-8")
    first = d.device("J1", "DEMO-CONN-4P")
    second = d.device("Z1", "DEMO-CONN-4P")
    live = d.terminal_strip("X1", "DEMO-TB-2.5-TWIN", 2).run("L", 2, bridged=True, rail=True)
    zero = d.terminal_strip("X2", "DEMO-TB-2.5-TWIN", 2).run("L", 2, bridged=True, rail=True)
    d.dc_supply("S", plus=live[1], minus=zero[1], voltage=24)
    d.series(ctrl.supply_system["S24V"], live[1].outer, wire=(BU, 0.5))
    d.series(ctrl.supply_system["SGND"], zero[1].outer, wire=(BU, 0.5))
    d.series(ctrl.supply_field["F24V1"], live[1].outer, wire=(BU, 0.5))
    d.series(ctrl.supply_field["FGND1"], zero[1].outer, wire=(BU, 0.5))
    for k in range(1, 5):
        d.series(first[str(k)], ctrl.X1[str(k)], wire=(BU, 0.5))
        d.series(second[str(k)], ctrl.X1[str(k + 4)], wire=(BU, 0.5))
    return fr.build(d, unit_document(cab)).model


def test_every_drawn_pin_of_the_connector_has_its_tag():
    model = _layout()
    (k4,) = (one.id for one in items(model).values() if one.tag == "K4")
    x1 = {f.id for f in functions(model).values() if f.item == k4 and f.name == "X1"}
    pin = {p.id: p.name for p in ports(model).values() if p.function in x1}
    owned = {p.value: p for p in pin}
    drawn = {owned[port]: one.page for one in symbol_subjects(model) for port in one.ports if port in owned}
    assert sorted(pin[p] for p in drawn) == [str(n) for n in range(1, 9)]
    texts = {(one.text, page) for page, drawing in drawn_pages(model).items() for one in drawing.texts}
    missing = sorted(pin[p] for p, page in drawn.items() if (port_designation(model, p), page) not in texts)
    assert missing == []
