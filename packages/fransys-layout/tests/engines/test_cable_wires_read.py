"""The cable engine's reader carries a harness block's single wires (HA-D6 P1, HA-H1 A1).

Models are invented from `demo_parts`; each fixture is built once per module.
"""

from typing import Any, NamedTuple

import fransys as fr
import pytest
from fransys.colours import BU
from fransys_author.surface import unit

from fransys_layout.engines.cable.read import drawable, read_blocks
from fransys_layout.engines.cable.read.subjects import block_pairs
from fransys_layout.geometry import text_width
from fransys_model.derive.cable_drawing import block_cables, block_wires, cable_subject
from fransys_model.vocab.tables import items, units
lazy from fransys_model.kernel import Id

_PLUG4, _PLUG2, _CABLE = "DEMO-CONN-4P", "DEMO-CONN-2P", "DEMO-CBL-4G1.5"


def _mixed(d: fr.Design) -> None:
    """MIX: one cable core on pin 1 and two wires on pins 2 and 3 of plugs J1 and J2."""
    with d.function("MIX", "Mixed loom"):
        loom = d.harness("MIX", place="L0")
        near = d.device("J1", _PLUG4, parent=loom, place="L0")
        far = d.device("J2", _PLUG4, parent=loom, place="L0")
        d.cable("MIX", _CABLE, parent=loom, name="cmix", place="L0").core(1, near[1], far[1])
        d.wire(near[2], far[2], wire=(BU, 0.5), label="SIG")
        d.wire(near[3], far[3], wire=(BU, 1.5))


def _others(d: fr.Design) -> None:
    """ONLY: two plugs, one wire, no cable. LINK: one wire between two pins of one plug.

    BARE: plugs and a cable, no wire.
    """
    with d.function("ONLY", "Wire-only loom"):
        loom = d.harness("ONLY", place="L0")
        near = d.device("J1", _PLUG2, parent=loom, place="L0")
        far = d.device("J2", _PLUG2, parent=loom, place="L0")
        d.wire(near[1], far[1], wire=(BU, 0.5))
    with d.function("LINK", "Link loom"):
        loom = d.harness("LINK", place="L0")
        plug = d.device("J1", _PLUG2, parent=loom, place="L0")
        d.wire(plug[1], plug[2], wire=(BU, 0.5))
    with d.function("BARE", "Bare loom"):
        loom = d.harness("BARE", place="L0")
        near = d.device("J1", _PLUG2, parent=loom, place="L0")
        far = d.device("J2", _PLUG2, parent=loom, place="L0")
        d.cable("BARE", _CABLE, parent=loom, name="cbare", place="L0").core(1, near[1], far[1])


class _Io(NamedTuple):
    J1: fr.Device


@unit("wired-loom", revision=1, interface_version=1, date="2026-10-07", text="First", by="XX")
def _wired_loom(d: fr.Design) -> _Io:
    """A unit holding the harness UH with one wire between its two plugs."""
    d.location("UL", "Unit place")
    with d.function("UH", "Unit loom"):
        loom = d.harness("UH", place="UL")
        near = d.device("J1", _PLUG2, parent=loom, place="UL")
        far = d.device("J2", _PLUG2, parent=loom, place="UL")
        d.wire(near[1], far[1], wire=(BU, 0.5))
    return _Io(J1=near)


@pytest.fixture(scope="module")
def model() -> fr.Model:
    """One design holding every harness shape the tests read."""
    d = fr.design("demo_parts")
    d.location("L0", "Workshop")
    _mixed(d)
    _others(d)
    d.add(_wired_loom, "U1", place="L0")
    return fr.build(d).model


def _item(model: fr.Model, key: str) -> Id[Any]:
    (found,) = [i for i, item in items(model).items() if "/".join(item.key) == key]
    return found


def _facts(model: fr.Model, harness: Id[Any], unit_id: Id[Any] | None = None):
    (found,) = [b for b in read_blocks(model) if (b.subject, b.unit) == (harness, unit_id)]
    return found


def test_a_cable_and_two_wires_are_one_block_with_continuing_keys(model: fr.Model) -> None:
    """Fails if `wires` drops or reorders a wire, restarts the keys at 1, or `cores` mis-orders.

    Mutation: `_wires` with its own `count(1)`; `cores` returning wires before cables' cores.
    """
    harness = _item(model, "MIX/MIX")
    facts = _facts(model, harness)
    drawn = block_wires(model, harness, None)
    assert len(facts.cables) == 1
    assert len(facts.wires) == 2
    assert [c.key for c in facts.cables[0].cores] == [1]
    assert [w.key for w in facts.wires] == [2, 3]
    assert [c.key for c in facts.cores] == [1, 2, 3]
    assert facts.cores == (*facts.cables[0].cores, *facts.wires)
    assert [w.conductor for w in facts.wires] == [w.conductor for w in drawn]
    assert [w.text_width for w in facts.wires] == [
        text_width(w.text, height=facts.text_height) for w in drawn
    ]
    assert not any(w.link for w in facts.wires)


def test_the_plugs_list_every_wire_on_its_pin(model: fr.Model) -> None:
    """Fails if the end rows or pins omit the wires: each plug's pins carry the block's cores.

    Mutation: `end_rows` or `drawn_pins` ignoring the wires.
    """
    facts = _facts(model, _item(model, "MIX/MIX"))
    assert {e.item for e in (*facts.top, *facts.bottom)} == {
        _item(model, "MIX/J1"),
        _item(model, "MIX/J2"),
    }
    assert len(facts.top) == len(facts.bottom) == 1
    for end in (*facts.top, *facts.bottom):
        landed = [c for pin in end.pins for c in pin.cores]
        assert landed == [core.conductor for core in facts.cores]


def test_a_wire_only_harness_is_a_drawable_block_with_no_cables(model: fr.Model) -> None:
    """Fails if `block_pairs` or `drawable` still demand a cable.

    Mutation: `drawable` returning `bool(block_cables(...))`; no wire harness in `block_pairs`.
    """
    harness = _item(model, "ONLY/ONLY")
    assert (None, harness) in block_pairs(model)
    assert block_cables(model, harness, None) == ()
    assert drawable(model, harness, None)
    facts = _facts(model, harness)
    assert facts.cables == ()
    assert [w.key for w in facts.wires] == [1]
    assert facts.harness_width is not None


def test_a_block_without_wires_has_none_and_a_loose_pin_is_no_block(model: fr.Model) -> None:
    """Fails if a cable-only block gains wires or a plug alone makes a block.

    Mutation: `_wires` reading every WIRE conductor of the model.
    """
    subject = cable_subject(model, _item(model, "BARE/cbare"))
    assert _facts(model, subject).wires == ()
    assert not drawable(model, _item(model, "MIX/J1"), None)


def test_a_unit_harness_has_the_absolute_and_the_unit_pair(model: fr.Model) -> None:
    """Fails if a wire harness of a unit lacks either reading.

    Mutation: `block_pairs` adding only `(None, h)`, or only `(unit, h)`.
    """
    harness = _item(model, "U1/UH/UH")
    (unit_id,) = units(model)
    assert (None, harness) in block_pairs(model)
    assert (unit_id, harness) in block_pairs(model)
    assert _facts(model, harness, unit_id).wires
    assert _facts(model, harness).wires


def test_a_wire_inside_one_plug_is_a_link(model: fr.Model) -> None:
    """Fails if `link` is not read from `row_links`.

    Mutation: `_wires` with `link=False`.
    """
    facts = _facts(model, _item(model, "LINK/LINK"))
    (wire,) = facts.wires
    assert wire.link
