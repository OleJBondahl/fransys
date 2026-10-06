"""Field case: a box device's contact stands in the circuit it switches, apart from its box.

The engineering shape: a redundancy module fed by two supplies (a box: two input groups, one
output) with a DC-OK contact 13/14. The contact feeds a relay coil K1 from the 24 V rail, and
K1's own contact reports to a PLC input.

The bug: the one contact function with a default symbol broke the box's merge condition, so the
module was drawn as three boxes (OUT, IN1, IN2) plus the contact.
The rule (decision layout-0123, owner 2026-10-06 A2): the module keeps its box-drawn functions as
one box and carries a contact image of its contacts; the contact stands in K1's circuit and shows
the box's position, the way a coil's contact shows its coil's.
"""

import dataclasses
import itertools
import re
import tempfile
from pathlib import Path

import fransys as fr
from fransys.colours import BN, BU

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.engines.schematic.read.write_keys import write_keys
from fransys_layout.geometry import overlaps
from fransys_layout.stages.texts.power import held_shapes
from fransys_model.derive.drawing_text import contact_image, cross_reference_text, tag_text
from fransys_model.layout import Label, LabelKind, PlacementView, SymbolPlacement, layout_of
from fransys_model.vocab.tables import functions, items, ports


def _built(*, rails: bool = True) -> tuple:
    """The plant; `rails=False` declares no supply: OUT+ and OUT- go to strip terminals."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    live = d.terminal_strip("X1", "DEMO-TB-2.5", 2).run("L", 2, bridged=True)
    zero = d.terminal_strip("X2", "DEMO-TB-2.5", 2).run("L", 2, bridged=True)
    with d.function("G", "Group"):
        psus = [d.device(f"T{n}", "DEMO-PSU-24") for n in (1, 2)]
        m1 = d.device("M1", "DEMO-RED-2IN")
        k1 = d.device("K1", "DEMO-RLY-2CO-24")
        di = d.device("U1", "DEMO-PLC-DI-2")
    for n, psu in enumerate(psus, start=1):
        group = getattr(m1, f"in_{n}")
        d.wire(psu.output["+"], group[f"{n}+"], wire=(BN, 1.5))
        d.wire(psu.output["-"], group[f"{n}-"], wire=(BU, 1.5))
    if rails:
        d.dc_supply("S", plus=live[1], minus=zero[1], voltage=24)
    d.wire(m1.out["+"], live[1].outer, wire=(BN, 1.5))
    d.wire(m1.out["-"], zero[1].outer, wire=(BU, 1.5))
    d.wire(live[2].outer, m1.dc_ok["13"], wire=(BN, 0.5))
    d.wire(m1.dc_ok["14"], k1.coil["A1"], wire=(BN, 0.5))
    d.wire(k1.coil["A2"], zero[2].outer, wire=(BU, 0.5))
    d.wire(live[2].outer, k1.co_1["11"], wire=(BN, 0.5))
    d.wire(k1.co_1["14"], di["1"], wire=(BN, 0.5))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    model = fr.build(d, doc).model
    return model, stage_results(model, read_inputs(model))[0].layout


def _item(model, tag: str):
    (item,) = (one.id for one in items(model).values() if one.key[-1] in (f"G/{tag}", tag))
    return item


def _contact(model):
    """The module's 13/14 contact function."""
    (contact,) = (f.id for f in functions(model).values() if f.name == "dc_ok")
    return contact


def _held_item(model, one):
    """The item a placed thing belongs to: a box names its item, any other thing its function."""
    held = functions(model)
    return held[one.function].item if one.function in held else one.function


def test_the_module_is_one_box_with_its_inputs_north_and_output_south() -> None:
    """One placed M1 box, no other placed thing of M1; IN1 and IN2 above the middle, OUT below."""
    model, layout = _built()
    m1 = _item(model, "M1")
    mine = [
        one
        for one in layout.placed
        if _held_item(model, one) == m1 and one.function != _contact(model)
    ]
    assert [one.function for one in mine] == [m1], "M1 is drawn as more than one box"
    box = mine[0]
    middle = box.geometry.keepout.y + box.geometry.keepout.height / 2
    names = {pin.name: pin.at.y for pin in box.geometry.ports}
    assert {"in_1", "in_2", "out"} <= {n.split(".")[0] for n in names}
    for name, y in names.items():
        assert (y < middle) == name.startswith(("in_1", "in_2")), f"{name} on the wrong side"


def test_the_contact_stands_in_k1s_circuit_and_shows_the_boxs_position() -> None:
    """The 13/14 contact is placed with K1 and its reference names the M1 box's place."""
    model, layout = _built()
    contact = _contact(model)
    (here,) = (one for one in layout.placed if one.function == contact)
    k1 = [one for one in layout.placed if _held_item(model, one) == _item(model, "K1")]
    assert here.page in {one.page for one in k1}
    (ref,) = (
        one
        for one in layout_of(model, Label).values()
        if one.kind is LabelKind.CROSS_REFERENCE and one.function == contact and one.slot == "tag"
    )
    partner = functions(model)[ports(model)[ref.partners[0].port].function]
    assert partner.item == _item(model, "M1")
    assert partner.id != contact, "the reference names the box, not the contact itself"
    (box,) = (one for one in layout.placed if one.function == _item(model, "M1"))
    assert ref.partners[0].x == box.at.x, "the reference is the box's own cell"
    assert re.fullmatch(r"\d[A-Z]", cross_reference_text(model, ref))


def test_the_contact_prints_its_item_tag_over_the_boxs_cell() -> None:
    """The contact carries the tag "-M1" as any contact does, though the box stands on the page."""
    model, _ = _built()
    contact = _contact(model)
    (tag,) = (
        one
        for one in layout_of(model, Label).values()
        if one.kind is LabelKind.TAG and one.function == contact and one.slot == "tag"
    )
    assert tag_text(model, contact) == "-M1"
    assert tag.function == contact


def test_the_image_under_the_module_lists_13_14_with_the_contacts_position() -> None:
    """The module's contact image lists 13-14 under NO with a place, and nothing under NC."""
    model, _ = _built()
    m1 = _item(model, "M1")
    held = functions(model)
    (label,) = (
        one
        for one in layout_of(model, Label).values()
        if one.kind is LabelKind.CROSS_REFERENCE
        and one.slot == "contacts"
        and one.function is not None
        and (one.function == m1 or (held.get(one.function) and held[one.function].item == m1))
    )
    no, nc = contact_image(model, label)
    assert len(no) == 1
    assert no[0].startswith("13-14 ")
    assert "N/A" not in no[0]
    assert nc == []


def test_the_box_stands_on_a_function_drawn_in_it_not_on_one_drawn_apart() -> None:
    """The box's placement is no contact's: with the lowest id drawn apart, the next one stands."""
    model, _ = _built()
    m1 = _item(model, "M1")
    inputs = read_inputs(model)
    (view,) = (s for s in inputs.functions if s.function == m1)
    ids = sorted(f.id for f in functions(model).values() if f.item == m1)
    apart = dataclasses.replace(
        view, function=ids[0], roles=dataclasses.replace(view.roles, item_view=False)
    )  # a spec of the lowest function, standing alone
    assert write_keys(model).item_function[m1] == ids[0]
    assert write_keys(model, (view, apart)).item_function[m1] == ids[1]
    (box,) = (
        one
        for one in layout_of(model, SymbolPlacement).values()
        if one.view is PlacementView.ITEM and functions(model)[one.function].item == m1
    )
    assert box.function != _contact(model)


def test_the_image_stands_clear_of_the_ink_below_the_module() -> None:
    """layout-0123: the image meets no marker, stub or power symbol of its page (one push-clear)."""
    _, layout = _built()
    (image,) = (
        one
        for one in layout.labels
        if one.slot == "contacts" and one.subject.kind == "item" and one.page == 1
    )
    ink = held_shapes(tuple(m for m in layout.markers if m.page == image.page))
    assert ink, "the page has a power symbol under the module"
    assert not [box for box in ink if overlaps(image.box, box)]


def _crosses(a, b, box) -> bool:
    """Whether the axis-aligned segment a-b enters the open rectangle `box`."""
    lo_x, hi_x = sorted((a.x, b.x))
    lo_y, hi_y = sorted((a.y, b.y))
    return lo_x < box.x + box.width and hi_x > box.x and lo_y < box.y + box.height and hi_y > box.y


def test_the_image_of_a_module_wired_to_terminals_crosses_no_wire() -> None:
    """layout-0123 F1: with OUT wired down to strip terminals, the image starts right of OUT-."""
    _, layout = _built(rails=False)
    (image,) = (
        one for one in layout.labels if one.slot == "contacts" and one.subject.kind == "item"
    )
    legs = [
        (route, one.at, two.at)
        for route in layout.routes
        if route.page == image.page
        for one, two in itertools.pairwise(route.points)
    ]
    assert legs
    assert not [leg for leg in legs if _crosses(leg[1], leg[2], image.box)]


def test_a_box_with_a_contact_is_not_a_coil() -> None:
    """layout-0123 F3: the box and K1's coil both own contacts apart; only the coil is a coil."""
    model, _ = _built()
    specs = {s.function: s for s in read_inputs(model).functions}
    box = specs[_item(model, "M1")]
    (coil,) = (s for s in specs.values() if s.kind == "coil")
    assert box.roles.contacts_apart
    assert not box.roles.coil
    assert coil.roles.coil
    assert coil.roles.contacts_apart
