"""Harness blocks (CT5-4, CD9, CD5 colouring, Q2 to Q7): a dashed box around the cable boxes.

Each test names its spec acceptance item and the probe that must make it fail. Models are
invented; nothing here names a real plant.
"""

from dataclasses import replace
from functools import cache
from itertools import pairwise
from types import SimpleNamespace
from typing import Any

import fransys_author
import fransys_parts
from cable_checks import assert_no_shared_stretch, assert_on_the_grid, assert_outside_the_box
from cable_facts import block_facts

from fransys_layout import lay_out_cables
from fransys_layout.engines.cable.place import _widest, block_pitch, place_block
from fransys_layout.engines.cable.read.facts import block_facts as block_facts_of
from fransys_layout.engines.cable.values import CableFacts, CoreFacts, EndFacts, PinFacts
from fransys_layout.engines.schematic.read.reading import profile_and_sheet
from fransys_layout.geometry import WIRING_GRID, text_width
from fransys_model.derive.cable_drawing import block_cables, cable_heading
from fransys_model.derive.passes.numbering import number as number_pass
from fransys_model.kernel import freeze, make_id, merge
from fransys_model.layout import (
    BlockRow,
    BoxKind,
    CableBlock,
    CableBox,
    CoreWire,
    EndBox,
    layout_of,
)
from fransys_model.vocab import Conductor, Item, Port

G = WIRING_GRID
_CABLE, _MOTOR = "DEMO-CBL-4G1.5", "DEMO-MOTOR-4KW"
_PROJECT: dict[str, Any] = {
    "title": "Harness blocks",
    "number": "P-1011",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}


def _design():
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-10-07", text="First issue", created="XX")
    return parts, d


def _lay(parts, d):
    frozen, _ = number_pass(freeze(merge(parts, d.draft())))
    model, findings = lay_out_cables(frozen)
    assert findings == ()
    return frozen, model


@cache
def _fan_out() -> SimpleNamespace:
    """Harness WH1: W1 (M1:U, V to M2:U, V, 5000 mm) and W2 (M1:W to M3:U) share end -M1."""
    parts, d = _design()
    c1, g = d.location("C1", "Cabinet"), d.group("G", "Group")
    harness = d.harness(tag="WH1", at=c1, group=g)
    m1, m2, m3 = (d.item(_MOTOR, tag=f"M{n}", parent=harness, at=c1, group=g) for n in (1, 2, 3))
    w1 = d.cable(_CABLE, tag="W1", parent=harness, at=c1, length_mm=5000)
    w1.core(1, m1["U"], m2["U"])
    w1.core(2, m1["V"], m2["V"])
    w2 = d.cable(_CABLE, tag="W2", parent=harness, at=c1)
    w2.core(1, m1["W"], m3["U"])
    frozen, model = _lay(parts, d)
    return SimpleNamespace(frozen=frozen, model=model, harness=harness.id, m1=m1.id, w1=w1.id)


@cache
def _short() -> SimpleNamespace:
    """Harness WH6: W1 (5000 mm) and W2, one core each, from -M1 to -M2 and -M3."""
    parts, d = _design()
    c1, g = d.location("C1", "Cabinet"), d.group("G", "Group")
    harness = d.harness(tag="WH6", at=c1, group=g)
    m1, m2, m3 = (d.item(_MOTOR, tag=f"M{n}", parent=harness, at=c1, group=g) for n in (1, 2, 3))
    w1 = d.cable(_CABLE, tag="W1", parent=harness, at=c1, length_mm=5000)
    w1.core(1, m1["U"], m2["U"])
    d.cable(_CABLE, tag="W2", parent=harness, at=c1).core(1, m1["V"], m3["U"])
    frozen, model = _lay(parts, d)
    return SimpleNamespace(frozen=frozen, model=model, harness=harness.id, w1=w1.id)


@cache
def _shared_lone() -> SimpleNamespace:
    """A lone cable W1 whose cores 1 and 2 both land on -M1:U (CD-H7)."""
    parts, d = _design()
    c1, g = d.location("C1", "Cabinet"), d.group("G", "Group")
    m1, m2 = (d.item(_MOTOR, tag=f"M{n}", at=c1, group=g) for n in (1, 2))
    cable = d.cable(_CABLE, tag="W1", at=c1, group=g)
    cable.core(1, m1["U"], m2["U"])
    cable.core(2, m1["U"], m2["V"])
    _, model = _lay(parts, d)
    return SimpleNamespace(model=model, cable=cable.id)


@cache
def _chain() -> SimpleNamespace:
    """Harness WH2, a daisy chain: W1 joins -X1 to -X2, W2 joins -X2 to -X3."""
    parts, d = _design()
    c1, g = d.location("C1", "Cabinet"), d.group("G", "Group")
    harness = d.harness(tag="WH2", at=c1, group=g)
    x1, x2, x3 = (d.item(_MOTOR, tag=f"X{n}", parent=harness, at=c1, group=g) for n in (1, 2, 3))
    d.cable(_CABLE, tag="W1", parent=harness, at=c1).core(1, x1["U"], x2["U"])
    d.cable(_CABLE, tag="W2", parent=harness, at=c1).core(1, x2["V"], x3["U"])
    _, model = _lay(parts, d)
    return SimpleNamespace(model=model, harness=harness.id, ends=(x1.id, x2.id, x3.id))


@cache
def _pair() -> SimpleNamespace:
    """Harness WH3: two independent cables, W1 from -A1 to -B1 and W2 from -A2 to -B2."""
    parts, d = _design()
    c1, g = d.location("C1", "Cabinet"), d.group("G", "Group")
    harness = d.harness(tag="WH3", at=c1, group=g)
    a1, b1, a2, b2 = (
        d.item(_MOTOR, tag=tag, parent=harness, at=c1, group=g) for tag in ("A1", "B1", "A2", "B2")
    )
    d.cable(_CABLE, tag="W1", parent=harness, at=c1).core(1, a1["U"], b1["U"])
    d.cable(_CABLE, tag="W2", parent=harness, at=c1).core(1, a2["U"], b2["U"])
    _, model = _lay(parts, d)
    return SimpleNamespace(model=model, harness=harness.id, tops=(a1.id, a2.id))


@cache
def _lone() -> SimpleNamespace:
    """A part-less harness WH4 holding one cable: the cable is the subject (model-0148)."""
    parts, d = _design()
    c1, g = d.location("C1", "Cabinet"), d.group("G", "Group")
    harness = d.harness(tag="WH4", at=c1, group=g)
    a, b = (d.item(_MOTOR, tag=tag, parent=harness, at=c1, group=g) for tag in ("A1", "B1"))
    cable = d.cable(_CABLE, tag="W1", parent=harness, at=c1)
    cable.core(1, a["U"], b["U"])
    _, model = _lay(parts, d)
    return SimpleNamespace(model=model, harness=harness.id, cable=cable.id)


@cache
def _shared() -> SimpleNamespace:
    """Harness WH5: W1 core 1 and W2 core 1 both land on -M1:U (CD-H7)."""
    parts, d = _design()
    c1, g = d.location("C1", "Cabinet"), d.group("G", "Group")
    harness = d.harness(tag="WH5", at=c1, group=g)
    m1, m2, m3 = (d.item(_MOTOR, tag=f"M{n}", parent=harness, at=c1, group=g) for n in (1, 2, 3))
    d.cable(_CABLE, tag="W1", parent=harness, at=c1).core(1, m1["U"], m2["U"])
    d.cable(_CABLE, tag="W2", parent=harness, at=c1).core(1, m1["U"], m3["U"])
    _, model = _lay(parts, d)
    return SimpleNamespace(model=model, harness=harness.id)


def _block(model, subject):
    """(head, boxes by kind, ends by item, wires) of the absolute block of `subject`, or None."""
    heads = [h for h in layout_of(model, CableBlock).values() if h.subject == subject]
    if not heads:
        return None
    (head,) = heads
    boxes = [b for b in layout_of(model, CableBox).values() if b.block == head.id]
    ends = [e for e in layout_of(model, EndBox).values() if e.block == head.id]
    wires = [w for w in layout_of(model, CoreWire).values() if w.block == head.id]
    return head, boxes, ends, wires


def _rect(box):
    return (box.x, box.y, box.x + box.width, box.y + box.height)


def test_a_two_cable_harness_is_one_dashed_box_around_two_solid_ones():
    """CD9, acceptance 7: one HARNESS box holds two CABLE boxes, W1 left of W2, none touching.

    Probe: draw the dashed box for every harness (the lone test below fails).
    """
    s = _fan_out()
    head, boxes, _, wires = _block(s.model, s.harness)
    (dash,) = (b for b in boxes if b.kind is BoxKind.HARNESS)
    cables = sorted((b for b in boxes if b.kind is BoxKind.CABLE), key=lambda b: b.x)
    assert len(cables) == 2
    assert len(wires) == 3
    assert cables[0].item == s.w1
    for box in cables:
        assert dash.x < box.x
        assert box.x + box.width < dash.x + dash.width
        assert dash.y < box.y
        assert box.y + box.height < dash.y + dash.height
    assert all(a.x + a.width < b.x for a, b in pairwise(cables))
    assert (dash.item, dash.external) == (s.harness, False)
    assert head.width >= dash.x + dash.width
    assert head.height >= dash.y + dash.height


def test_a_lone_cable_harness_has_a_cable_block_and_no_dashed_box():
    """CD9, acceptance 7: the part-less one-cable harness is its cable; no HARNESS box.

    Probe: draw the dashed box for every harness.
    """
    s = _lone()
    assert _block(s.model, s.harness) is None
    _, boxes, _, _ = _block(s.model, s.cable)
    assert [b.kind for b in boxes] == [BoxKind.CABLE]


def test_two_cables_landing_on_one_end_draw_one_end_box_with_every_pin_landed():
    """CD9 Q9, acceptance 14: -M1 has one end box; its three pins are landed by either cable.

    Probe: one end box per cable and item.
    """
    s = _fan_out()
    _, _, ends, _ = _block(s.model, s.harness)
    assert sorted(e.item for e in ends).count(s.m1) == 1
    (m1,) = (e for e in ends if e.item == s.m1)
    assert m1.row is BlockRow.TOP
    assert [pin.landed for pin in m1.pins][:3] == [True] * 3
    assert len(ends) == 3


def test_harness_block_geometry_is_clean():
    """CD8, acceptance 4, 5, 18: on the grid; no run enters a cable box; no shared stretch."""
    for s in (_fan_out(), _chain(), _pair()):
        _, boxes, ends, wires = _block(s.model, s.harness)
        runs = [run for w in wires for run in (w.run_a, w.run_b)]
        assert_on_the_grid(runs)
        assert_no_shared_stretch(runs)
        for box in boxes:
            if box.kind is BoxKind.CABLE:
                assert_outside_the_box(runs, (box.x, box.y, box.width, box.height))
        for record in (*boxes, *ends):
            assert all(v % G == 0 for v in (record.x, record.y, record.width, record.height))


def test_a_daisy_chain_draws_with_its_middle_end_below():
    """CD5 Q1, acceptance 20: X1 and X3 on top, X2 below; both cables and both cores drawn.

    Probe: CD5's old rows (the lowest-ranked end alone on top).
    """
    s = _chain()
    _, boxes, ends, wires = _block(s.model, s.harness)
    rows = {e.item: e.row for e in ends}
    x1, x2, x3 = s.ends
    assert (rows[x1], rows[x2], rows[x3]) == (BlockRow.TOP, BlockRow.BOTTOM, BlockRow.TOP)
    assert len(wires) == 2
    assert sum(b.kind is BoxKind.CABLE for b in boxes) == 2


def test_two_independent_cables_draw_each_from_its_own_top_end():
    """CD5 Q1, acceptance 20: A1 and A2 on top, B1 and B2 below.

    Probe: CD5's old rows.
    """
    s = _pair()
    _, _, ends, wires = _block(s.model, s.harness)
    assert {e.item for e in ends if e.row is BlockRow.TOP} == set(s.tops)
    assert len(wires) == 2


def test_a_short_cable_box_grows_the_pitch_until_its_heading_fits():
    """CD9 Q2, acceptance 21: a one-core cable headed `-W1, 5000 mm` in a harness.

    The pitch is above the plain pitch rule's, and no heading passes its box's edge. Probe: keep
    the pitch at its plain measure.
    """
    s = _short()
    head, boxes, _, _ = _block(s.model, s.harness)
    profile, _, _ = profile_and_sheet(s.model)
    cables = {c.cable: c for c in block_cables(s.frozen, s.harness, None)}
    for box in (b for b in boxes if b.kind is BoxKind.CABLE):
        heading = cable_heading(s.frozen, cables[box.item], None)
        wide = text_width(heading, height=profile.text_height) + 2 * profile.marker_padding
        assert box.width >= wide
    assert cable_heading(s.frozen, cables[s.w1], None).endswith("5000 mm")
    plain = block_pitch(_widest(block_facts_of(s.frozen, s.harness, None)))
    assert head.pitch > plain
    assert head.pitch % 16 == 0


def test_a_pin_two_cores_land_on_gets_no_block():
    """CD-H7, Q7: two cores of one cable, or of two cables, on -M1:U: the block is not drawn.

    Probe: drop the shared-pin test from `drawable`; the lone cable then draws.
    """
    assert _block(_shared().model, _shared().harness) is None
    assert _block(_shared_lone().model, _shared_lone().cable) is None


def _two_cable_facts(*, interleaved: bool):
    """Two cables over one bottom end; with `interleaved`, cable B stands between A's columns."""
    ids = [make_id(Port, (f"p{n}",)) for n in range(6)]
    owner = [make_id(Item, (n,)) for n in ("t1", "t2", "b")]

    def end(item, *ports, blank=False):
        pins = tuple(PinFacts(port=p, landed=True, marking_width=16) for p in ports)
        return EndFacts(item=item, dashed=False, blank=blank, label_width=16, pins=pins)

    def core(key, a, b):
        return CoreFacts(
            key=key, conductor=make_id(Conductor, (str(key),)), end_a=a, end_b=b, text_width=16
        )

    top = (end(owner[0], ids[0], ids[1]), end(owner[1], ids[2]))
    cables = (
        CableFacts(
            cable=make_id(Item, ("a",)),
            external=False,
            heading_width=16,
            cores=(core(1, ids[0], ids[3]), core(2, ids[2] if interleaved else ids[1], ids[4])),
        ),
        CableFacts(
            cable=make_id(Item, ("b",)),
            external=False,
            heading_width=16,
            cores=(core(3, ids[1] if interleaved else ids[2], ids[5]),),
        ),
    )
    bottom = (end(owner[2], ids[3], ids[4], ids[5]),)
    return replace(block_facts([(0, 0)]), cables=cables, top=top, bottom=bottom, harness_width=16)


def test_interleaved_cable_columns_get_no_block():
    """CD-H6, Q6: cable A on top pins 1 and 3 with cable B on pin 2 between: no block.

    Probe: drop the overlap test from `cable_boxes`. The side-by-side twin draws.
    """
    assert place_block(_two_cable_facts(interleaved=False)) is not None
    assert place_block(_two_cable_facts(interleaved=True)) is None
