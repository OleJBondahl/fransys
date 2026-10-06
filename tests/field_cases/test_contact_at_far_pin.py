"""Field case: a contact wired to a PLC input channel stands under that channel (V5, 2026-10-02).

The engineering shape: a PLC input module K1 with two wired channels in one group, and in a second
group two contactors K2 and K3, each with its coil wired to a lamp and its auxiliary contact wired
to one channel. A third contactor K4 has an auxiliary contact with a wire to channel 3 and a wire
to a lamp, so it has no single far pin.

The bug: chain discovery homed one contactor's contacts under its channel; the other contactors'
contacts stayed in their own group, bundled with the device's other contacts, so the move of a
lone contact column did not reach them. The module also holds power pins, so it is no all-channel
box: the channel pins are flagged per port. The main contact has one wire, so it is drawn.

The rule (CONVENTIONS-V06 V5, decision layout-0099): a contact whose one wire goes to a pin in
another group is homed under that pin, once, and references its coil; a contact with a second
wire stays home.
"""

import tempfile
from itertools import combinations, pairwise
from pathlib import Path

import fransys as fr
from fransys.colours import BU

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.geometry import GENERIC_BOX_KEY, WIRING_GRID, symbol_geometry
from fransys_layout.geometry.symbols import channel_pitch
from fransys_model.layout import PowerSymbol, SymbolPlacement, layout_of
from fransys_model.vocab.tables import functions, items, ports


def _plant(d, *, split: bool = False) -> None:
    with d.function("G0", "PLC group"):
        module = d.device("K1", "DEMO-PLC-DI-4P")
    with d.function("G1", "Contactor group") as g1:
        lamps = {n: d.device(f"P{n}", "DEMO-LAMP-24") for n in (2, 3, 4)}
        contactors = {
            n: d.device(f"K{n}", "DEMO-CTR-3P-NC") for n in (2, 3, 4) if not split or n != 3
        }
    d.layout.break_before(g1)
    if split:
        with d.function("G2", "Second contactor group") as g2:
            contactors[3] = d.device("K3", "DEMO-CTR-3P-NC")
        d.layout.break_before(g2)
    for number, contactor in contactors.items():
        d.wire(contactor.coil["A1"], lamps[number].lamp["1"], wire=(BU, 0.5))
        d.wire(contactor.main["1"], lamps[number].lamp["1"], wire=(BU, 0.5))  # layout-0112: wired
        channel = getattr(module, f"di_{number - 1}")[str(number - 1)]
        d.wire(contactor.aux["14"], channel, wire=(BU, 0.5))
    d.wire(contactors[4].aux["13"], lamps[4].lamp["2"], wire=(BU, 0.5))


def _built(*, split: bool = False) -> tuple:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    _plant(d, split=split)
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    model = fr.build(d, doc).model
    results, _ = stage_results(model, read_inputs(model))
    return model, results.layout


def _placed(model, layout, tag: str, name: str) -> list:
    tag_of = {i.id: i.tag for i in items(model).values()}
    return [
        p
        for f in functions(model).values()
        for p in layout.placed
        if p.function == f.id and f.name == name and tag_of[f.item] == tag
    ]


def _pin_x(placed, port: str) -> int:
    (geometry,) = (g for g in placed.geometry.ports if g.name == port)
    return placed.at.x + geometry.at.x


def _port_y(placed, port: str) -> int:
    (geometry,) = (g for g in placed.geometry.ports if g.name == port)
    return placed.at.y + geometry.at.y


def test_each_single_wire_contact_stands_once_under_its_channel() -> None:
    model, layout = _built()
    (box,) = (p for p in layout.placed if p.function in {i.id for i in items(model).values()})
    for number in (2, 3):
        (contact,) = _placed(model, layout, f"K{number}", "aux")
        assert (contact.drawing_set, contact.page) == (box.drawing_set, box.page)
        assert contact.at.y > box.at.y
        assert _pin_x(contact, "out") == _pin_x(box, f"di_{number - 1}.{number - 1}")


def test_each_moved_contact_references_its_coil_and_the_coil_lists_it() -> None:
    model, layout = _built()
    for number in (2, 3):
        (contact,) = _placed(model, layout, f"K{number}", "aux")
        (coil,) = _placed(model, layout, f"K{number}", "coil")
        refs = [one for one in layout.labels if one.kind.name == "CROSS_REFERENCE"]
        (home,) = (r for r in refs if r.subject == contact.function)
        assert [(p.drawing_set, p.page) for p in home.partners] == [(coil.drawing_set, coil.page)]
        table = [r for r in refs if r.subject == coil.function]
        assert any(
            (p.drawing_set, p.page) == (contact.drawing_set, contact.page)
            for r in table
            for p in r.partners
        )


def test_a_contact_with_a_second_wire_stays_in_its_own_group() -> None:
    model, layout = _built()
    (contact,) = _placed(model, layout, "K4", "aux")
    (coil,) = _placed(model, layout, "K4", "coil")
    assert (contact.drawing_set, contact.page) == (coil.drawing_set, coil.page)


def test_a_box_stays_on_its_group_page_when_its_contacts_come_from_two_groups() -> None:
    """layout-0103: the contacts of two groups under one box never home the box on the last page."""
    model, layout = _built(split=True)
    (box,) = (p for p in layout.placed if p.function in {i.id for i in items(model).values()})
    coils = [_placed(model, layout, f"K{n}", "coil")[0] for n in (2, 3)]
    assert all((box.drawing_set, box.page) != (c.drawing_set, c.page) for c in coils)
    assert box.page == min(p.page for p in layout.placed if p.drawing_set == box.drawing_set)
    for number in (2, 3):
        (contact,) = _placed(model, layout, f"K{number}", "aux")
        assert (contact.drawing_set, contact.page) == (box.drawing_set, box.page)


def _boxes(model) -> list:
    return [p for p in layout_of(model, SymbolPlacement).values() if p.symbol == GENERIC_BOX_KEY]


def test_channel_pins_stand_one_and_a_half_pole_pitches_apart_and_their_texts_keep_the_gap() -> (
    None
):
    """V5 pitch: pins 1.5 pole pitches apart (texts widen it only where needed), no text nearer."""
    model, layout = _built()
    (box,) = (p for p in _boxes(model) if any("di_" in n for n in p.ports))
    south = sorted(
        x for x, side in zip(box.port_offsets, box.sides, strict=True) if side.value == "s"
    )
    assert [b - a for a, b in pairwise(south)] == [channel_pitch()] * (len(south) - 1)
    assert channel_pitch() * 2 == 3 * (symbol_geometry("circuit-breaker", poles=3).ports[2].at.x)
    placed = [_placed(model, layout, f"K{n}", "aux")[0] for n in (2, 3)]
    x0, x1 = min(p.at.x for p in placed), max(p.at.x for p in placed)
    y0 = min(p.at.y for p in placed)
    under = [
        label.box
        for label in layout.labels
        if label.page == placed[0].page
        and x0 - 20 <= label.box.x <= x1 + 90
        and label.box.y >= y0 - 40
    ]
    assert len(under) >= 6, "the contacts' texts were not found: the check would pass over nothing"
    pins = sorted(p.at.x for p in placed)
    owner = lambda box: max(x for x in pins if x <= box.x)  # noqa: E731 -- local, one use
    for one, other in combinations(under, 2):
        if owner(one) == owner(other):
            continue  # one contact's own texts sit by design
        dx = max(one.x, other.x) - min(one.x + one.width, other.x + other.width)
        dy = max(one.y, other.y) - min(one.y + one.height, other.y + other.height)
        assert max(dx, dy) >= WIRING_GRID, (one, other)


def _rail_plant(d) -> None:
    """One contactor K2 whose aux 14 goes to a DI channel and whose aux 13 goes to a 24 V rail."""
    with d.function("G0", "PLC group"):
        module = d.device("K1", "DEMO-PLC-DI-4P")
    with d.function("G1", "Contactor group") as g1:
        zero = d.terminal_strip("X1", "DEMO-TB-2.5", 1)
        rail = d.terminal_strip("X2", "DEMO-TB-2.5", 2).run("R", 2, bridged=True)
        d.dc_supply("S", plus=rail[1], minus=zero[1], voltage=24)
        contactor = d.device("K2", "DEMO-CTR-3P-NC")
    d.layout.break_before(g1)
    d.wire(contactor.aux["14"], module.di_1["1"], wire=(BU, 0.5))
    d.wire(contactor.aux["13"], rail[1].outer, wire=(BU, 0.5))


def test_a_contact_hangs_straight_down_and_its_column_ends_in_a_downward_supply_bar() -> None:
    """V5, layout-0103: pin, 98/14, contact turned 180, 97/13, supply bar pointing down; no wire
    turns back (the round-3 U-turn put the contact beside the line and a horizontal wire to it)."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    _rail_plant(d)
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    model = fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)).model
    layout = stage_results(model, read_inputs(model))[0].layout
    (box,) = (p for p in layout.placed if p.function in {i.id for i in items(model).values()})
    (contact,) = _placed(model, layout, "K2", "aux")
    line = _pin_x(box, "di_1.1")
    assert _pin_x(contact, "out") == line, "the contact stands in its channel pin's column"
    assert _port_y(contact, "out") < _port_y(contact, "in"), "98/14 above 97/13"
    (route,) = (r for r in layout.routes if {p.at.x for p in r.points} == {line})
    assert len({p.at.x for p in route.points}) == 1, "no horizontal wire, no turn back"
    port_of = {(p.function, p.name): pid for pid, p in ports(model).items()}
    (bar,) = (
        s
        for s in layout_of(model, PowerSymbol).values()
        if s.port == port_of[contact.function, "13"]
    )
    assert bar.symbol == "power-supply"
    assert bar.y > _port_y(contact, "in"), "the bar stands below the contact"
    assert bar.orientation.name == "R180", bar.orientation


def _plant_16(d) -> None:
    with d.function("G0", "PLC group"):
        module = d.device("K1", "DEMO-PLC-DI-16")
    with d.function("G1", "Contactor group") as g1:
        contactors = [d.device(f"K{n + 1}", "DEMO-CTR-3P-NC") for n in range(1, 17)]
        lamps = [d.device(f"P{n}", "DEMO-LAMP-24") for n in range(1, 17)]
    d.layout.break_before(g1)
    for number, (contactor, lamp) in enumerate(zip(contactors, lamps, strict=True), start=1):
        d.wire(contactor.coil["A1"], lamp.lamp["1"], wire=(BU, 0.5))
        channel = getattr(module, f"di_{number}")[str(number)]
        d.wire(contactor.aux["14"], channel, wire=(BU, 0.5))


def test_a_sixteen_channel_module_fits_one_page_with_a_contact_under_every_channel() -> None:
    """V5 (layout-0103): 16 channels at 1.5 pole pitches fit a page; none falls back to a reference.

    Engineering shape: a 16-channel DI module in its own group, every channel wired from the
    auxiliary contact of a contactor in a second group. The bug: at the house column spacing the
    module was 16 columns wide, so its widened slots could not fit and its contacts stayed home.
    """
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    _plant_16(d)
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    model = fr.build(d, doc).model
    results, _ = stage_results(model, read_inputs(model))
    layout = results.layout
    (box,) = (p for p in layout.placed if p.function in {i.id for i in items(model).values()})
    keepout = box.geometry.keepout
    assert box.at.x + keepout.x + keepout.width <= read_inputs(model).sheet.content_width
    for number in range(1, 17):
        (contact,) = _placed(model, layout, f"K{number + 1}", "aux")
        assert (contact.drawing_set, contact.page) == (box.drawing_set, box.page), number
        assert _pin_x(contact, "out") == _pin_x(box, f"di_{number}.{number}"), number
