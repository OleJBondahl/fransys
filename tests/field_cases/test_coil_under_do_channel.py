"""Field case: a relay coil wired to a PLC output channel stands under that channel (V5).

The engineering shape: a PLC output module K1 with two channels in one group, and in a second
group two relays K2 and K3. Each coil is wired from one channel; its other end goes to a 0 V rail
strip (bridged terminals, not drawn) shared with a lamp, and each relay's changeover contact
feeds the lamp of the page. Two coils on two channels of one module box.

The bug: the first coil was homed under its channel by chain discovery; the second kept its own
column in its relay's group, because a module box is one function with every channel's wire on it,
so the single-pin test saw two wires. The coil's contacts then referenced a coil on a page that
did not show its channel.

The rule (CONVENTIONS-V06 V5, decision layout-0099): a coil wired to a PLC output channel is drawn
under that channel, its other end draws the rail's ground symbol, and its contacts reference it.
"""

import tempfile
from pathlib import Path

import fransys as fr
from fransys.colours import BU

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_model.layout import PowerSymbol, layout_of
from fransys_model.vocab.tables import functions, items, ports


def _built() -> tuple:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G0", "PLC group"):
        module = d.device("K1", "DEMO-PLC-DO-2")
    with d.function("G1", "Relay group"):
        live = d.terminal_strip("X1", "DEMO-TB-2.5", 1)
        rail = d.terminal_strip("X2", "DEMO-TB-2.5", 4).run("R", 4, bridged=True)
        d.dc_supply("S", plus=live[1], minus=rail[1], voltage=24)
        for number in (2, 3):
            relay = d.device(f"K{number}", "DEMO-RLY-2CO-24")
            lamp = d.device(f"P{number}", "DEMO-LAMP-24")
            channel = getattr(module, f"do_{number - 1}")[str(number - 1)]
            d.wire(channel, relay.coil["A1"], wire=(BU, 0.5))
            d.wire(relay.co_1["14"], lamp.lamp["1"], wire=(BU, 0.5))
            d.wire(relay.coil["A2"], rail[2 * number - 3].outer, wire=(BU, 0.5))
            d.wire(lamp.lamp["2"], rail[2 * number - 2].outer, wire=(BU, 0.5))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    model = fr.build(d, doc).model
    results, _ = stage_results(model, read_inputs(model))
    return model, results.layout


def _one(model, layout, tag: str, name: str):
    """The only placement of function `name` of item `tag`."""
    tag_of = {i.id: i.tag for i in items(model).values()}
    (found,) = (
        p
        for f in functions(model).values()
        for p in layout.placed
        if p.function == f.id and f.name == name and tag_of[f.item] == tag
    )
    return found


def _pin_x(placed, port: str) -> int:
    """The page x of port `port` of `placed`."""
    (geometry,) = (g for g in placed.geometry.ports if g.name == port)
    return placed.at.x + geometry.at.x


def test_each_coil_stands_under_its_own_channel_of_the_module_box() -> None:
    model, layout = _built()
    (box,) = (p for p in layout.placed if p.function in {i.id for i in items(model).values()})
    for number in (2, 3):
        coil = _one(model, layout, f"K{number}", "coil")
        assert (coil.drawing_set, coil.page) == (box.drawing_set, box.page)
        assert coil.at.y > box.at.y
        assert _pin_x(coil, "in") == _pin_x(box, f"do_{number - 1}.{number - 1}")


def test_each_moved_coil_draws_the_rail_ground_and_its_contact_references_it() -> None:
    model, layout = _built()
    grounds = {s.port for s in layout_of(model, PowerSymbol).values() if s.symbol == "ground"}
    port_of = {(ports(model)[p].function, ports(model)[p].name): p for p in ports(model)}
    for number in (2, 3):
        coil = _one(model, layout, f"K{number}", "coil")
        assert port_of[coil.function, "A2"] in grounds
        contact = _one(model, layout, f"K{number}", "co_1")
        (ref,) = (
            one
            for one in layout.labels
            if one.subject == contact.function and one.kind.name == "CROSS_REFERENCE"
        )
        assert [(p.drawing_set, p.page) for p in ref.partners] == [(coil.drawing_set, coil.page)]
