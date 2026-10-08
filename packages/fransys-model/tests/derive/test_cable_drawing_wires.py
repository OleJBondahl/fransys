"""A harness block counts its single wires as cores: rows, pins, links, key texts (HA-H1 A1)."""

from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
import pytest
from fransys.colours import BU

from fransys_model.derive.cable_drawing import (
    DrawnWire,
    block_cables,
    block_drawn,
    block_wires,
    drawn_blocks,
    drawn_pins,
    end_rows,
    row_links,
    wire_harness_subjects,
)
from fransys_model.derive.drawing_text import wire_text
from fransys_model.kernel import Id, make_id
from fransys_model.vocab.core import Unit
from fransys_model.vocab.tables import items

_PLUG4 = "DEMO-CONN-4P"
_PLUG2 = "DEMO-CONN-2P"
_CABLE = "DEMO-CBL-4G1.5"


def _mixed(d: fr.Design) -> None:
    """MIX: one cable core on pin 1 and two wires on pins 2 and 3 of plugs J1 and J2."""
    with d.function("MIX", "Mixed loom"):
        loom = d.harness("MIX", place="L0")
        near = d.device("J1", _PLUG4, parent=loom, place="L0")
        far = d.device("J2", _PLUG4, parent=loom, place="L0")
        d.cable("MIX", _CABLE, parent=loom, name="cmix", place="L0").core(1, near[1], far[1])
        d.wire(near[2], far[2], wire=(BU, 0.5), label="SIG")
        d.wire(near[3], far[3], wire=(BU, 1.5))


def _only(d: fr.Design) -> None:
    """ONLY: two plugs and one wire on pin 1, no cable. LINK: one wire from pin 1 to pin 2 of J1."""
    with d.function("ONLY", "Wire-only loom"):
        loom = d.harness("ONLY", place="L0")
        near = d.device("J1", _PLUG2, parent=loom, place="L0")
        far = d.device("J2", _PLUG2, parent=loom, place="L0")
        d.wire(near[1], far[1], wire=(BU, 0.5))
    with d.function("LINK", "Link loom"):
        loom = d.harness("LINK", place="L0")
        plug = d.device("J1", _PLUG2, parent=loom, place="L0")
        d.wire(plug[1], plug[2], wire=(BU, 0.5))


def _bare(d: fr.Design) -> None:
    """BARE: a harness with plugs and a cable but no wire. Loose wire LA1-LA2 is on no harness."""
    with d.function("BARE", "Bare loom"):
        loom = d.harness("BARE", place="L0")
        near = d.device("J1", _PLUG2, parent=loom, place="L0")
        far = d.device("J2", _PLUG2, parent=loom, place="L0")
        d.cable("BARE", _CABLE, parent=loom, name="cbare", place="L0").core(1, near[1], far[1])
    with d.function("LOOSE", "Loose"):
        a = d.device("LA1", _PLUG2, place="L0")
        b = d.device("LA2", _PLUG2, place="L0")
    d.wire(a[1], b[1], wire=(BU, 0.5))


@pytest.fixture(scope="module")
def model() -> fr.Model:
    """One design holding every harness shape the tests below read."""
    d = fr.design("demo_parts")
    d.location("L0", "Workshop")
    _mixed(d)
    _only(d)
    _bare(d)
    return fr.build(d).model


def _item(model: fr.Model, key: str) -> Id[Any]:
    (found,) = [i for i, item in items(model).items() if "/".join(item.key) == key]
    return found


def test_a_mixed_harness_lists_its_wires_with_their_key_texts(model: fr.Model) -> None:
    """Catches a `block_wires` that drops the colour, the gauge or the label, or its order."""
    wires = block_wires(model, _item(model, "MIX/MIX"), None)
    assert [type(w) for w in wires] == [DrawnWire, DrawnWire]
    assert [(w.index, w.text) for w in wires] == [
        (1, "-MIX-J1:2 -MIX-J2:2 BU 0.5 mm²"),
        (2, "-MIX-J1:3 -MIX-J2:3 BU 1.5 mm²"),
    ]


def test_a_mixed_block_keeps_its_cable_cores_first_in_the_pin_cells(model: fr.Model) -> None:
    """Catches wires missing from `drawn_pins` or sorted before the cable core."""
    harness, j1 = _item(model, "MIX/MIX"), _item(model, "MIX/J1")
    (cable,) = block_cables(model, harness, None)
    wires = block_wires(model, harness, None)
    pins = drawn_pins(model, harness, j1, None)
    assert [(p.marking, p.landed) for p in pins] == [
        ("1", True), ("2", True), ("3", True), ("4", False),
    ]  # fmt: skip
    assert [p.cores for p in pins[:3]] == [
        (cable.cores[0].conductor,),
        (wires[0].conductor,),
        (wires[1].conductor,),
    ]
    assert pins[3].cores == ()


def test_a_mixed_block_has_two_end_boxes_one_per_row_and_no_link(model: fr.Model) -> None:
    """Catches a wire that adds an end box of its own or makes a row link."""
    harness = _item(model, "MIX/MIX")
    top, bottom = end_rows(model, harness, None)
    assert {*top, *bottom} == {_item(model, "MIX/J1"), _item(model, "MIX/J2")}
    assert len(top) == len(bottom) == 1
    assert row_links(model, harness, None) == ()
    assert len(block_cables(model, harness, None)) == 1


def test_a_wire_only_harness_draws_its_ends_and_free_pins(model: fr.Model) -> None:
    """Catches a block that is empty when it has no cable, or a connector end with no free pins."""
    harness, j1 = _item(model, "ONLY/ONLY"), _item(model, "ONLY/J1")
    assert block_cables(model, harness, None) == ()
    (wire,) = block_wires(model, harness, None)
    top, bottom = end_rows(model, harness, None)
    assert {*top, *bottom} == {j1, _item(model, "ONLY/J2")}
    pins = drawn_pins(model, harness, j1, None)
    assert [(p.marking, p.landed, p.cores) for p in pins] == [
        ("1", True, (wire.conductor,)),
        ("2", False, ()),
    ]


def test_a_wire_inside_one_plug_is_a_row_link(model: fr.Model) -> None:
    """Catches a wire whose two ends sit in one row not being listed in `row_links`."""
    harness = _item(model, "LINK/LINK")
    (wire,) = block_wires(model, harness, None)
    assert row_links(model, harness, None) == (wire.conductor,)
    assert end_rows(model, harness, None) == ((_item(model, "LINK/J1"),), ())


def test_no_wires_for_a_harness_without_any_or_a_loose_wire(model: fr.Model) -> None:
    """Catches a loose wire, or another harness's wire, leaking into a block."""
    bare, loose_end = _item(model, "BARE/BARE"), _item(model, "LOOSE/LA1")
    assert block_wires(model, bare, None) == ()
    assert block_wires(model, loose_end, None) == ()
    assert wire_harness_subjects(model) == tuple(
        sorted(_item(model, f"{tag}/{tag}") for tag in ("MIX", "ONLY", "LINK"))
    )


def test_a_unit_reading_holds_the_wires_of_the_harnesses_of_that_unit() -> None:
    """Catches a dropped unit check (a non-member unit reads wires) or a non-unit-relative text."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(title="Wires", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    u = d.scope("cab").unit("demo-pump-cabinet", revision=1, interface="1")
    u.revision(1, date="2026-01-01", text="First release", created="XX")
    c1, grp = u.location("C1", "Cabinet"), u.group("G", "Group")
    w1 = u.harness(name="w1", tag="W1", at=c1, group=grp)
    p1 = u.item(_PLUG2, tag="P1", parent=w1, at=c1, group=grp)
    p2 = u.item(_PLUG2, tag="P2", parent=w1, at=c1, group=grp)
    u.wiring(colour="BU", gauge="0.5")(p1["1"], p2["1"])
    u.boundary(u.item(_PLUG2, tag="X1", at=c1, group=grp))
    model = fr.build(parts, d.draft()).model
    harness = next(i for i, item in items(model).items() if item.key[-1] == "w1")
    unit = items(model)[harness].unit
    assert unit is not None
    other: Id[Unit] = make_id(Unit, ("other",))
    (wire,) = block_wires(model, harness, unit)
    assert block_wires(model, harness, other) == ()
    assert len(block_wires(model, harness, None)) == 1
    assert wire.text.startswith(wire_text(model, wire.conductor, unit=unit))
    assert wire.text.endswith(" BU 0.5 mm²")


def test_a_block_is_drawn_when_it_has_a_cable_or_a_wire_and_not_otherwise(model: fr.Model) -> None:
    """Catches a predicate that asks cables alone, wires alone, or answers yes for a bare loom."""
    drawn = {
        key: block_drawn(model, _item(model, key), None)
        for key in ("MIX/MIX", "ONLY/ONLY", "BARE/cbare")
    }
    assert drawn == {"MIX/MIX": True, "ONLY/ONLY": True, "BARE/cbare": True}
    assert block_drawn(model, _item(model, "BARE/J1"), None) is False


def test_the_drawn_blocks_list_wire_only_and_cable_harnesses_and_no_plug(model: fr.Model) -> None:
    """Catches a list that leaves out a wire-only harness, or lists a block that has nothing."""
    listed = {subject for _, subject in drawn_blocks(model)}
    assert _item(model, "ONLY/ONLY") in listed
    assert _item(model, "MIX/MIX") in listed
    assert _item(model, "BARE/cbare") in listed
    assert _item(model, "BARE/J1") not in listed
    assert all(block_drawn(model, subject, unit) for unit, subject in drawn_blocks(model))
