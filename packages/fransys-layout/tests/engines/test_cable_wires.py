"""The cable placer draws a harness's single wires with no cable box (HA-D6 P1, HA-H1 A1).

A wire stands from pin to pin through the band where the cable boxes stand, its key text beside
the line. Models are invented from `demo_parts`; each is built once per module.
"""

from dataclasses import replace
from itertools import pairwise
from typing import Any

import fransys as fr
import pytest
from cable_facts import block_facts
from fransys.colours import BU

from fransys_layout import lay_out_cables
from fransys_layout.engines.cable.place import place_block
from fransys_layout.engines.cable.read import read_blocks
from fransys_model.derive.cable_drawing import block_wires
from fransys_model.layout import BoxKind, CableBlock, CableBox, CoreWire, layout_of
from fransys_model.vocab.tables import items

_PLUG4, _PLUG2, _CABLE = "DEMO-CONN-4P", "DEMO-CONN-2P", "DEMO-CBL-4G1.5"


def _looms(d: fr.Design) -> None:
    """MIX: a four-core cable between plugs J1, J2 and two wires between J3, J4.

    ONLY: two wires. LINK: a wire between two pins of one plug.
    """
    with d.function("MIX", "Mixed loom"):
        loom = d.harness("MIX", place="L0")
        plugs = [d.device(f"J{n}", _PLUG4, parent=loom, place="L0") for n in (1, 2, 3, 4)]
        cable = d.cable("MIX", _CABLE, parent=loom, name="cmix", place="L0")
        for pin in (1, 2, 3, 4):
            cable.core(pin, plugs[0][pin], plugs[1][pin])
        d.wire(plugs[2][1], plugs[3][1], wire=(BU, 0.5), label="SIG")
        d.wire(plugs[2][2], plugs[3][2], wire=(BU, 1.5))
    with d.function("ONLY", "Wire-only loom"):
        loom = d.harness("ONLY", place="L0")
        near = d.device("J1", _PLUG4, parent=loom, place="L0")
        far = d.device("J2", _PLUG4, parent=loom, place="L0")
        d.wire(near[1], far[1], wire=(BU, 0.5))
        d.wire(near[2], far[2], wire=(BU, 1.5))
    with d.function("LINK", "Link loom"):
        loom = d.harness("LINK", place="L0")
        plug = d.device("J1", _PLUG2, parent=loom, place="L0")
        d.wire(plug[1], plug[2], wire=(BU, 0.5))
    with d.function("LINKED", "Wire and link loom"):
        loom = d.harness("LINKED", place="L0")
        near = d.device("J1", _PLUG4, parent=loom, place="L0")
        far = d.device("J2", _PLUG4, parent=loom, place="L0")
        d.wire(near[1], far[1], wire=(BU, 0.5))
        d.wire(near[3], near[4], wire=(BU, 0.5))


@pytest.fixture(scope="module")
def built() -> Any:
    """The looms' model after the cable pass, and that pass's findings."""
    d = fr.design("demo_parts")
    d.location("L0", "Workshop")
    _looms(d)
    return lay_out_cables(fr.build(d).model)


def _harness(model: fr.Model, key: str) -> Any:
    (found,) = [i for i, item in items(model).items() if "/".join(item.key) == f"{key}/{key}"]
    return found


class _Drawn:
    """One harness block as the placer left it: boxes, wires and the wires' conductors."""

    def __init__(self, model: fr.Model, key: str) -> None:
        subject = _harness(model, key)
        (head,) = [h for h in layout_of(model, CableBlock).values() if h.subject == subject]
        self.boxes = [b for b in layout_of(model, CableBox).values() if b.block == head.id]
        core_wires = [w for w in layout_of(model, CoreWire).values() if w.block == head.id]
        mine = {w.conductor for w in block_wires(model, subject, None)}
        self.wires = [w for w in core_wires if w.conductor in mine]
        self.cables = [b for b in self.boxes if b.kind is BoxKind.CABLE]
        (self.text_height,) = {f.text_height for f in read_blocks(model) if f.subject == subject}

    @property
    def dash(self) -> Any:
        (dash,) = [b for b in self.boxes if b.kind is BoxKind.HARNESS]
        return dash


def _junction(wire: Any) -> Any:
    """The point where a wire's two runs meet, or None when they share no end point."""
    ends_a = {(p.x, p.y) for p in (wire.run_a[0], wire.run_a[-1])}
    ends_b = {(p.x, p.y) for p in (wire.run_b[0], wire.run_b[-1])}
    (shared,) = ends_a & ends_b
    return shared


def test_a_mixed_harness_keeps_its_cable_box_and_draws_wires_beside_it(built: Any) -> None:
    """Fails if a wire gets a cable box, a cable loses its own, or a wire is not drawn.

    Mutation: `cable_boxes` taking a box per wire; `_spans` dropping the cable's span.
    """
    drawn = _Drawn(built[0], "MIX")
    assert len(drawn.boxes) == 2
    assert len(drawn.cables) == 1
    assert drawn.dash.kind is BoxKind.HARNESS
    assert len(drawn.wires) == 2


def test_no_wire_is_drawn_inside_a_cable_box(built: Any) -> None:
    """Acceptance 10: a wire's column is clear of every cable box, and its line runs the band.

    The upper run starts above the box band and the two runs meet at the band's bottom edge, so
    the line is one piece through the band. Mutation: `_spans` giving the wires' columns to a
    cable (its box then spans them); `upper_stop` ending a wire's upper run at the box's top.
    """
    drawn = _Drawn(built[0], "MIX")
    (cable,) = drawn.cables
    for wire in drawn.wires:
        x, y = _junction(wire)
        assert not cable.x <= x <= cable.x + cable.width
        assert y == cable.y + cable.height
        tops = [p.y for run in (wire.run_a, wire.run_b) for p in run if p.x == x and p.y < y]
        assert tops
        assert min(tops) < cable.y


def test_a_wire_text_stands_beside_its_line_in_the_box_band(built: Any) -> None:
    """The text sits in the cable boxes' y-range and clear of the line by half its height.

    Mutation: `text_x` returning the axis (the line strikes through the text); a text outside
    the band.
    """
    drawn = _Drawn(built[0], "MIX")
    (cable,) = drawn.cables
    for wire in drawn.wires:
        x, _ = _junction(wire)
        assert cable.y <= wire.text_y <= cable.y + cable.height
        assert wire.text_x != x
        assert wire.text_x - x >= drawn.text_height / 2


def test_the_dashed_box_encloses_every_wire_key(built: Any) -> None:
    """The harness box reaches past each wire's text, which stands to the right of its line.

    Mutation: `envelope` ending at the last column plus half a pitch (the key crosses the edge).
    """
    for key in ("MIX", "ONLY"):
        drawn = _Drawn(built[0], key)
        edge = drawn.dash.x + drawn.dash.width
        assert all(w.text_x + drawn.text_height // 2 < edge for w in drawn.wires)


def test_a_wire_only_harness_has_one_dashed_box_around_every_wire(built: Any) -> None:
    """No cable boxes; the harness box holds each wire's column; nothing is an ERROR.

    Mutation: `_frame` returning None without cable boxes; the envelope left out of the frame.
    """
    drawn = _Drawn(built[0], "ONLY")
    assert drawn.cables == []
    assert len(drawn.wires) == 2
    for wire in drawn.wires:
        x, y = _junction(wire)
        assert drawn.dash.x < x < drawn.dash.x + drawn.dash.width
        assert drawn.dash.y < y <= drawn.dash.y + drawn.dash.height
        assert wire.run_a
        assert wire.run_b
    assert built[1] == ()


def test_a_wire_between_two_pins_of_one_plug_is_a_row_link(built: Any) -> None:
    """A link has no cable box, no vertical wire and a horizontal run on its track.

    Mutation: `links_of` reading only the cables' cores (the link is dropped or drawn as a core).
    """
    drawn = _Drawn(built[0], "LINK")
    assert drawn.cables == []
    (wire,) = drawn.wires
    ys = {p.y for p in wire.run_a}
    assert len(ys) > 1
    track = [(p, q) for p, q in pairwise(wire.run_a) if p.y == q.y and p.x != q.x]
    assert len(track) == 1


def test_a_link_only_harness_has_no_dashed_frame_but_a_mixed_one_keeps_it(built: Any) -> None:
    """Layout-0157 L1: only links, no frame; a point-to-point wire beside a link keeps it.

    Mutation: `_frame` always returning the dashed box (the link-only harness gets one).
    """
    assert not [b for b in _Drawn(built[0], "LINK").boxes if b.kind is BoxKind.HARNESS]
    linked = _Drawn(built[0], "LINKED")
    assert linked.dash.kind is BoxKind.HARNESS
    assert len(linked.wires) == 2


def test_a_wire_standing_inside_a_cable_span_is_refused() -> None:
    """Three columns; the middle one is a wire between a cable's two cores: no block.

    Mutation: dropping the `crosses` test from `_frame` (the wire is drawn through the box).
    """
    facts = block_facts([(0, 0), (1, 1), (2, 2)])
    (cable,) = facts.cables
    middle = cable.cores[1]
    split = replace(cable, cores=(cable.cores[0], cable.cores[2]))
    refused = replace(facts, cables=(split,), wires=(middle,), harness_width=40)
    assert place_block(refused) is None
    drawn = replace(facts, cables=(replace(cable, cores=cable.cores[:2]),), wires=(cable.cores[2],))
    assert place_block(replace(drawn, harness_width=40)) is not None
