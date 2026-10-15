"""Field case: a 16-channel PLC output card keeps every coil under its own pin (R1, R11).

The engineering shape: a 16-channel digital output module in its own group. Each channel drives a
relay coil; each relay's contact switches a lamp between a 24 V rail and a 0 V rail, all in a
second group.

The bug: 13 of 16 coils hung under the box. The fit gate (layout-0074) sent the coils of channels
4, 6 and 8 back to the load pages behind off-page markers, and the box printed its pins
`1 2 3 5 7 10 9 12 11 14 13 16 15 4 6 8`. The box and all 16 coil columns fit the page: 8 to 13
channels passed, 14 was the first to fail.

The rule (layout-0208, amended by R1 and R11): a channel's coil hangs under that channel always,
and the box prints its pins in marking order.
"""

import tempfile
from functools import cache
from pathlib import Path

import fransys as fr
from fransys.colours import BU
from fransys_el import OPTIONS

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_model.vocab.tables import functions, items, ports

COUNT = 16


@cache
def _built() -> tuple:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G0", "PLC outputs"):
        module = d.device("K1", f"DEMO-PLC-DO-{COUNT}")
    with d.function("G1", "Relays and lamps"):
        live = d.terminal_strip("X1", "DEMO-TB-2.5", COUNT + 1).run("L", COUNT + 1, bridged=True)
        rail = d.terminal_strip("X2", "DEMO-TB-2.5", 2 * COUNT + 1)
        rail = rail.run("R", 2 * COUNT + 1, bridged=True)
        d.dc_supply("S", plus=live[1], minus=rail[1], voltage=24)
        for i in range(1, COUNT + 1):
            relay = d.device(f"K{i + 1}", "DEMO-RLY-2CO-24")
            lamp = d.device(f"P{i}", "DEMO-LAMP-24")
            channel = getattr(module, f"do_{i}")[str(i)]
            d.detail.wire(channel, relay.coil["A1"], wire=(BU, 0.5))
            d.detail.wire(relay.coil["A2"], rail[2 * i].outer, wire=(BU, 0.5))
            d.detail.wire(live[i + 1].outer, relay.co_1["11"], wire=(BU, 0.5))
            d.detail.wire(relay.co_1["14"], lamp.lamp["1"], wire=(BU, 0.5))
            d.detail.wire(lamp.lamp["2"], rail[2 * i + 1].outer, wire=(BU, 0.5))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    model = fr.build(d, doc).model
    results, _ = stage_results(model, read_inputs(model, options=OPTIONS))
    return model, results.layout


def _named(model) -> dict:
    """Each function's (item tag, function name)."""
    tag_of = {i.id: i.tag for i in items(model).values()}
    return {f.id: (tag_of[f.item], f.name) for f in functions(model).values()}


def _box_pins(model, layout) -> dict:
    """Each channel's (box placement, pin x): the card is drawn as one box, keyed by its item."""
    (card,) = (i.id for i in items(model).values() if i.tag == "K1")
    (box,) = (p for p in layout.placed if p.function == card)
    return {
        int(g.name.split("_")[1].split(".")[0]): (box, box.at.x + g.at.x)
        for g in box.geometry.ports
    }


def test_every_coil_hangs_under_its_own_channel_pin() -> None:
    model, layout = _built()
    named = _named(model)
    pins = _box_pins(model, layout)
    coils = {
        int(named[p.function][0][1:]) - 1: p
        for p in layout.placed
        if named.get(p.function, ("", ""))[1] == "coil"
    }
    assert sorted(coils) == list(range(1, COUNT + 1))
    for channel, coil in coils.items():
        box, x = pins[channel]
        (inlet,) = (g for g in coil.geometry.ports if g.name == "in")
        assert (coil.drawing_set, coil.page) == (box.drawing_set, box.page), channel
        assert coil.at.x + inlet.at.x == x, channel


def test_no_channel_wire_leaves_by_a_marker() -> None:
    """No coil reference back to the card; the coils' A2 rail markers show markers are read."""
    model, layout = _built()
    named = _named(model)
    by_id = ports(model)
    marked = [
        (*named.get(by_id[m.port].function, ("", "")), by_id[m.port].name) for m in layout.markers
    ]
    assert not [n for n in marked if n[0] == "K1" or (n[1], n[2]) == ("coil", "A1")]
    assert [n for n in marked if (n[1], n[2]) == ("coil", "A2")]


def test_the_card_prints_its_pins_in_marking_order() -> None:
    model, layout = _built()
    pins = _box_pins(model, layout)
    assert sorted(pins, key=lambda channel: pins[channel][1]) == list(range(1, COUNT + 1))
