"""Multi-end cable blocks through the public author API (CT5-3 P3; CD5, CD8, CD9; acceptance 4, 18).

F1 is a 1:3 fan-out (one strip, three motors), F2 a 2:2 swap in a unit's reading (two strips of
the unit, two external motors). Each test names the probe that must make it fail.
"""

from dataclasses import replace
from functools import cache
from itertools import pairwise
from types import SimpleNamespace
from typing import Any

import fransys_author
import fransys_parts
import pytest
from cable_checks import assert_no_shared_stretch, assert_on_the_grid, assert_outside_the_box
from cable_facts import block_facts

from fransys_layout import lay_out_cables
from fransys_layout.engines.cable.place import place_block
from fransys_layout.engines.schematic.read.reading import profile_and_sheet
from fransys_layout.geometry import WIRING_GRID, LayoutError, snap_up, text_width
from fransys_model.derive.cable_drawing import block_cables, core_text, end_label
from fransys_model.derive.passes.numbering import number as number_pass
from fransys_model.kernel import freeze, merge
from fransys_model.layout import BlockRow, CableBlock, CableBox, CoreWire, EndBox, layout_of

_PROJECT: dict[str, Any] = {
    "title": "Cable bends",
    "number": "P-1011",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}
G = WIRING_GRID
_CABLE, _MOTOR, _TB = "DEMO-CBL-4G1.5", "DEMO-MOTOR-4KW", "DEMO-TB-2.5"


def _design():
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-10-07", text="First issue", created="XX")
    return parts, d


def _laid_out(parts, d):
    frozen, _ = number_pass(freeze(merge(parts, d.draft())))
    return frozen, lay_out_cables(frozen)[0]


@cache
def _f1() -> SimpleNamespace:
    """Strip -X1 with three terminals, cores 1-3 to the U port of motors -M1, -M2, -M3."""
    parts, d = _design()
    er, fld = d.location("ER", "Engine room"), d.location("FLD", "Field")
    g, gf = d.group("ER", "Cabinet"), d.group("FLD", "Field")
    strip = d.strip("X1", at=er)
    terminals = [strip.terminal(_TB, group=g) for _ in range(3)]
    motors = [d.item(_MOTOR, tag=f"M{n}", at=fld, group=gf) for n in (1, 2, 3)]
    cable = d.cable(_CABLE, tag="W1", at=er, group=g)
    for n, (terminal, motor) in enumerate(zip(terminals, motors, strict=True), start=1):
        cable.core(n, terminal.outer, motor["U"])
    frozen, model = _laid_out(parts, d)
    return SimpleNamespace(frozen=frozen, model=model, cable=cable.id)


def _f2_design(*, reverse: bool = False):
    """Unit strips -X5, -X6 (two terminals each), external motors -M1, -M2; cores swap columns.

    Core 1 X5:1-M1.U, 2 X5:2-M2.U, 3 X6:1-M1.V, 4 X6:2-M2.V, so the bottom row's pins run
    M1.U M1.V M2.U M2.V against the top's X5:1 X5:2 X6:1 X6:2: cores 2 and 3 swap.
    """
    parts, d = _design()
    fld, gf = d.location("FLD", "Field"), d.group("FLD", "Field")
    cab = d.scope("cab").unit("demo-pump-cabinet", revision=1, interface="1")
    cab.revision(1, date="2026-01-01", text="First release", created="XX")
    c1, grp = cab.location("C1", "Cabinet"), cab.group("G1", "Group")
    x5, x6 = cab.strip("X5", at=c1), cab.strip("X6", at=c1)
    t = [x5.terminal(_TB, group=grp), x5.terminal(_TB, group=grp)]
    t += [x6.terminal(_TB, group=grp), x6.terminal(_TB, group=grp)]
    m1 = d.item(_MOTOR, tag="M1", at=fld, group=gf, external=True)
    m2 = d.item(_MOTOR, tag="M2", at=fld, group=gf, external=True)
    cable = cab.cable(_CABLE, name="w", at=c1)
    cores = [(1, t[0], m1["U"]), (2, t[1], m2["U"]), (3, t[2], m1["V"]), (4, t[3], m2["V"])]
    for n, terminal, far in cores[::-1] if reverse else cores:
        cable.core(n, terminal.outer, far)
    return parts, d, cable


@cache
def _f2() -> SimpleNamespace:
    parts, d, cable = _f2_design()
    frozen, model = _laid_out(parts, d)
    return SimpleNamespace(frozen=frozen, model=model, cable=cable.id)


def _block(model, cable, *, in_unit: bool = False):
    """The block of `cable` (in its unit's reading when `in_unit`): head, box, ends, wires."""
    heads = layout_of(model, CableBlock).values()
    (head,) = (h for h in heads if h.subject == cable and (h.unit is not None) == in_unit)
    ends = sorted(
        (e for e in layout_of(model, EndBox).values() if e.block == head.id),
        key=lambda e: (e.row is BlockRow.BOTTOM, e.x),
    )
    wires = [w for w in layout_of(model, CoreWire).values() if w.block == head.id]
    (box,) = (b for b in layout_of(model, CableBox).values() if b.block == head.id)
    return head, box, ends, wires


def _runs(wires):
    return [run for w in wires for run in (w.run_a, w.run_b)]


def _check(block):
    _, box, _, wires = block
    runs = _runs(wires)
    assert_no_shared_stretch([w.run_b[::-1] for w in wires])
    assert_outside_the_box(runs, (box.x, box.y, box.width, box.height))
    assert_on_the_grid(runs)


def _label_gaps(s, head, bottom):
    """The gap of each neighbouring pair: one pitch, or more where their labels would come
    within a grid unit (CD8). One-pin boxes: the centres stand `apart` from each other."""
    profile, _, _ = profile_and_sheet(s.frozen)
    widths = [
        text_width(end_label(s.frozen, e.item, None), height=profile.text_height) for e in bottom
    ]
    apart = [(a + b + 1) // 2 + G for a, b in pairwise(widths)]
    return [max(head.pitch, snap_up(one) - head.pitch) for one in apart]


def test_f1_fan_out_draws_with_bends_and_its_ends_one_pitch_apart():
    """Acceptance 4, Q5: a 1:3 block bends, no shared stretch; end boxes of a row stand one pitch
    apart, or as far as their labels need. Probe: `row_xs` spacing the end boxes three pitches."""
    s = _f1()
    head, _, ends, wires = _block(s.model, s.cable)
    top, *bottom = ends
    assert (top.row, [e.row for e in bottom]) == (BlockRow.TOP, [BlockRow.BOTTOM] * 3)
    assert [len(e.pins) for e in ends] == [3, 1, 1, 1]
    assert [b.x - (a.x + a.width) for a, b in pairwise(bottom)] == _label_gaps(s, head, bottom)
    assert any(len(w.run_b) > 2 for w in wires)
    assert all(len(w.run_a) == 2 for w in wires)  # the upper band is straight
    _check(_block(s.model, s.cable))


def test_f2_swap_in_a_unit_draws_one_jog_and_core_texts_follow_the_top_row():
    """Acceptance 4 and 19: the 2:2 swap bends; each core text stands on its column, in the top
    row's order, with its core number. Probe: `_split` returning None (the cycle stays)."""
    s = _f2()
    head, box, ends, wires = _block(s.model, s.cable, in_unit=True)
    unit = head.unit
    assert unit is not None
    cables = block_cables(s.frozen, s.cable, unit)
    texts = {c.conductor: core_text(c) for c in cables[0].cores}
    assert [len(e.pins) for e in ends] == [2, 2, 2, 2]
    assert sorted(len(w.run_b) for w in wires) == [2, 2, 4, 6]  # one jog
    by_x = sorted(wires, key=lambda w: w.text_x)
    assert [texts[w.conductor].split()[0] for w in by_x] == ["1", "2", "3", "4"]
    assert box.x <= by_x[0].text_x
    assert by_x[-1].text_x <= box.x + box.width
    _check(_block(s.model, s.cable, in_unit=True))


def test_f2_is_the_same_whatever_order_the_cores_are_added_in():
    """Layout invariant 5, through the model: cores added in reverse order give equal records and
    the same digest. The listing-order probe is stages/test_channel's shuffle test."""
    parts, d, _ = _f2_design(reverse=True)
    _, backward = _laid_out(parts, d)
    forward = _f2().model
    assert dict(layout_of(backward, CoreWire)) == dict(layout_of(forward, CoreWire))
    assert backward.digests == forward.digests


def test_a_row_of_drawn_and_blank_ends_is_refused():
    """The placer's uniform-row rule: a blank end beside a drawn one raises. Probe: the check
    removed from `_place_rows`."""
    facts = block_facts([(0, 0), (0, 1)])
    mixed = replace(facts, bottom=(facts.bottom[0], replace(facts.bottom[1], blank=True)))
    with pytest.raises(LayoutError):
        place_block(mixed)
