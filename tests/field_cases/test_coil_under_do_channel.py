"""Field case: a relay coil wired to a PLC output channel stands under that channel (V5).

The engineering shape: a PLC output module K1 with two channels in one group, and in a second
group two relays K2 and K3. Each coil is wired from one channel; its other end goes to a 0 V rail
strip (bridged terminals, not drawn) shared with a lamp, and each relay's changeover contact
feeds the lamp of the page. Two coils on two channels of one module box.

The bug: the first coil was homed under its channel by chain discovery; the second kept its own
column in its relay's group, because a module box is one function with every channel's wire on it,
so the single-pin test saw two wires. The coil's contacts then referenced a coil on a page that
did not show its channel.

The rule (decision layout-0099): a coil wired to a PLC output channel is drawn
under that channel, its other end draws the rail's ground symbol, and its contacts reference it.
"""

import tempfile
from pathlib import Path

import fransys as fr
from _drawn_facts import symbol_subjects
from _drawn_pages import drawn_pages
from fransys.colours import BU

from fransys_layout.geometry import GENERIC_BOX_KEY
from fransys_layout.geometry.symbols import symbol_geometry
from fransys_model.layout import Orientation, Page, PowerSymbol, layout_of
from fransys_model.vocab.tables import functions, items, ports


def _built():
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
            d.detail.wire(channel, relay.coil["A1"], wire=(BU, 0.5))
            d.detail.wire(relay.co_1["14"], lamp.lamp["1"], wire=(BU, 0.5))
            d.detail.wire(relay.coil["A2"], rail[2 * number - 3].outer, wire=(BU, 0.5))
            d.detail.wire(lamp.lamp["2"], rail[2 * number - 2].outer, wire=(BU, 0.5))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    return fr.build(d, doc).model


def _one(model, tag: str, name: str, symbol: str | None = None) -> tuple:
    """The page and the only drawn symbol of function `name` of item `tag` (of `symbol`)."""
    tag_of = {i.id: i.tag for i in items(model).values()}
    wanted = {
        f.id.value for f in functions(model).values() if f.name == name and tag_of[f.item] == tag
    }
    (found,) = (s for s in symbol_subjects(model) if s.owner in wanted and symbol in (None, s.key))
    return found.page, found


def _home(model, page) -> tuple:
    """The drawing set and the page a drawn symbol stands on."""
    return layout_of(model, Page)[page].drawing_set, page


def _pin_x(drawn, port: str) -> int:
    """The page x of port `port` of `drawn`."""
    if drawn.key == GENERIC_BOX_KEY:
        return drawn.x + dict(drawn.offsets)[port]
    geometry = symbol_geometry(drawn.key, poles=drawn.poles, orientation=Orientation[drawn.orient])
    (found,) = (g for g in geometry.ports if g.name == port)
    return drawn.x + found.at.x


def _module_box(model) -> tuple:
    (box,) = (
        (page, s)
        for page, drawing in drawn_pages(model).items()
        for s in drawing.symbols
        if s.key == GENERIC_BOX_KEY and any(n.startswith("do_") for n, _ in s.offsets)
    )
    return box


def test_each_coil_stands_under_its_own_channel_of_the_module_box() -> None:
    model = _built()
    box_page, box = _module_box(model)
    for number in (2, 3):
        coil_page, coil = _one(model, f"K{number}", "coil", "operating-device")
        assert _home(model, coil_page) == _home(model, box_page)
        assert coil.y > box.y
        assert _pin_x(coil, "in") == _pin_x(box, f"do_{number - 1}.{number - 1}")


def test_each_moved_coil_draws_the_rail_ground() -> None:
    model = _built()
    grounds = {s.port for s in layout_of(model, PowerSymbol).values() if s.symbol == "ground"}
    port_of = {(ports(model)[p].function, ports(model)[p].name): p for p in ports(model)}
    for number in (2, 3):
        _, coil = _one(model, f"K{number}", "coil", "operating-device")
        fid = next(f.id for f in functions(model).values() if f.id.value == coil.owner)
        assert port_of[fid, "A2"] in grounds


def _gap(model, fact: str):
    """A fact the page Drawing lacks (strict xfail, GAP-FLIP-DRAWING-SUBJECT)."""
    msg = f"GAP-FLIP-DRAWING-SUBJECT: no {fact} for {model.digest}"
    raise AssertionError(msg)


def test_each_moved_coils_contact_reference_names_the_coils_page() -> None:
    model = _built()
    _gap(model, "cross-reference partner pages")
