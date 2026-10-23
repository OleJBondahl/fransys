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
from _drawn_facts import Placed, symbol_subjects
from fransys.colours import BU

from fransys_model.layout import LinkMarker, layout_of
from fransys_model.vocab.tables import functions, ports

COUNT = 16


@cache
def _built() -> fr.BuildResult:
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
    return fr.build(d, doc)


def _box_pins() -> tuple[object, Placed, dict[int, int]]:
    """The card's drawn box and its page; each channel's pin x (box origin plus the pin offset)."""
    model = _built().model
    page, box = next((r.page, r) for r in symbol_subjects(model) if r.key == "generic-box")
    offsets = dict(box.offsets)
    return page, box, {i: box.x + offsets[f"do_{i}.{i}"] for i in range(1, COUNT + 1)}


def test_every_coil_hangs_under_its_own_channel_pin() -> None:
    page, _, pins = _box_pins()
    model = _built().model
    coils = {
        int(r.tag[1:]) - 1: (r.page, r)
        for r in symbol_subjects(model)
        if r.key == "operating-device"
    }
    assert sorted(coils) == list(range(1, COUNT + 1))
    for channel, (coil_page, coil) in coils.items():
        assert coil_page == page, channel
        assert coil.x == pins[channel], channel


def test_no_channel_wire_leaves_by_a_marker() -> None:
    """No coil reference back to the card: no marker stands on a card pin or a coil's A1."""
    model = _built().model
    marked = [
        (functions(model)[ports(model)[m.port].function].name, ports(model)[m.port].name)
        for m in layout_of(model, LinkMarker).values()
    ]
    assert [one for one in marked if one[1] == "A1" or one[0] == "box"] == []


def test_the_card_prints_its_pins_in_marking_order() -> None:
    """The card is two-sided (BOX-SIDES): the first pins stand on the north side, then the rest."""
    _, box, pins = _box_pins()
    sides = dict(box.sides)
    north = [i for i in pins if sides[f"do_{i}.{i}"] == "n"]
    south = [i for i in pins if sides[f"do_{i}.{i}"] == "s"]
    order = sorted(north, key=pins.__getitem__) + sorted(south, key=pins.__getitem__)
    assert order == list(range(1, COUNT + 1))
