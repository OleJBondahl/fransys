"""`fold_level` (model-0199): the group fold, pass-through lines and folded stubs."""

import dataclasses

import pytest
from fold_builders import CTL_BOX, SUP, SUP_BOX, fold_plant
from overview_builders import item_id

from fransys_model.derive import (
    ItemKind,
    OverviewLinkKind,
    StubPlace,
    fold_level,
    overview_fold_stub_lines,
    stub_ends,
)
from fransys_model.kernel import SchemaError
from fransys_model.layout import OverviewRef, OverviewRefKind


def _id(ref: OverviewRef) -> object:
    """The one id a reference holds."""
    return ref.unit or ref.item or ref.node


def _boxes(level):
    return {b.lines[0]: b for b in level.boxes}


def test_each_group_folds_to_one_box_with_its_counts() -> None:
    """=SUP holds 2 devices and 2 strips, =CTL 2 devices and a unit; X9 is in a strips box."""
    model, unit, _ = fold_plant()
    level = fold_level(model, unit)
    boxes = _boxes(level)
    assert level.folded
    assert set(boxes) == {"=SUP", "=CTL", "Terminal strips (1)"}
    sup, ctl = boxes["=SUP"], boxes["=CTL"]
    assert (sup.items, sup.units, sup.strips, sup.inner_lines) == (2, 0, 2, 8)
    assert (ctl.items, ctl.units, ctl.strips, ctl.inner_lines) == (2, 1, 0, 2)
    strips = boxes["Terminal strips (1)"]
    assert (strips.key.kind, strips.terminals, strips.item_kind) == (
        OverviewRefKind.STRIPS,
        1,
        ItemKind.STRIP,
    )
    assert sup.lines[1] == "SUP group"


def test_one_line_joins_a_pair_of_boxes_and_a_group_counts_its_inner_lines_apart() -> None:
    """P1-K1 is the one line between the groups; wires inside a group are no line."""
    model, unit, _ = fold_plant()
    level = fold_level(model, unit)
    pairs = {(line.a.kind, line.b.kind, line.count) for line in level.lines}
    assert pairs == {
        (OverviewRefKind.GROUP, OverviewRefKind.GROUP, 1),
        (OverviewRefKind.GROUP, OverviewRefKind.STRIPS, 1),
        (OverviewRefKind.GROUP, OverviewRefKind.STRIPS, 1),
    }
    assert len(level.lines) == 3


def test_a_terminal_that_passes_two_wires_through_is_one_labelled_line() -> None:
    """A12: P1 to D1 through X1:t1 is one line labelled -X1; two terminals of X2 are -X2 x 2."""
    model, unit, _ = fold_plant()
    level = fold_level(model, unit, SUP_BOX)
    through = {line.label: line for line in level.lines if line.strip is not None}
    assert set(through) == {"-X1", "-X2 x 2"}
    assert through["-X2 x 2"].terminals == 2
    assert through["-X2 x 2"].strip == item_id("x2")
    ends = {_id(through["-X1"].a), _id(through["-X1"].b)}
    assert ends == {item_id("p1"), item_id("d1")}


def test_a_bridged_terminal_keeps_its_strip_as_a_box() -> None:
    """A12: X1's t2 and t3 are bridged, so X1 is a box with a line to each end; X2 draws none."""
    model, unit, _ = fold_plant()
    level = fold_level(model, unit, SUP_BOX)
    drawn = {_id(box.key) for box in level.boxes}
    assert item_id("x1") in drawn
    assert item_id("x2") not in drawn
    kept = {frozenset((_id(line.a), _id(line.b))) for line in level.lines if line.strip is None}
    assert kept == {
        frozenset((item_id("p1"), item_id("x1"))),
        frozenset((item_id("x1"), item_id("d1"))),
    }
    notes = {note.strip: note for note in level.strips}
    assert (notes[item_id("x1")].held, notes[item_id("x1")].terminals) == (True, 3)
    assert (notes[item_id("x2")].held, notes[item_id("x2")].terminals) == (False, 2)


def test_a_pass_through_to_another_group_ends_at_a_stub() -> None:
    """X9 (no group) passes K2 to D1: in =SUP a stub to =CTL stands at D1; X9 is listed."""
    model, unit, _ = fold_plant()
    level = fold_level(model, unit, SUP_BOX)
    at_d1 = [s for s in level.stubs if _id(s.box) == item_id("d1")]
    assert [(s.place, s.far, s.count) for s in at_d1] == [(StubPlace.GROUP, "=CTL", 1)]
    note = next(n for n in level.strips if n.strip == item_id("x9"))
    assert (note.held, note.terminals) == (False, 1)


def test_far_ends_in_one_unit_fold_to_one_stub_that_opens_to_both() -> None:
    """A13: wires to F1 and F2 of unit U9 are one stub of count 2 whose members are the two ends."""
    model, unit, _ = fold_plant()
    level = fold_level(model, unit)
    (folded,) = [s for s in level.stubs if s.place is StubPlace.UNIT]
    assert (folded.far, folded.count) == ("-U9", 2)
    assert {m.far for m in folded.members} == {"-U9-F1", "-U9-F2"}
    assert all(m.count == 1 for m in folded.members)
    (single,) = [s for s in level.stubs if s.place is StubPlace.END]
    assert single.far == "-B1"
    assert single.members[0].count == 1


def test_an_opened_group_keeps_the_fold_of_its_stubs() -> None:
    """In =CTL, K1 and K2 each reach U9 through their own stub; =SUP is a group stub."""
    model, unit, _ = fold_plant()
    level = fold_level(model, unit, CTL_BOX)
    places = sorted((_id(s.box), s.place.value, s.far) for s in level.stubs)
    assert (item_id("k1"), "unit", "-U9") in places
    assert (item_id("k2"), "unit", "-U9") in places
    assert (item_id("k1"), "group", "=SUP") in places


def test_a_unit_with_one_group_opens_straight_to_its_devices() -> None:
    """A14: =SUP alone is one group, so the unit opens to all its boxes and not to one group box."""
    model, unit, _ = fold_plant(ctl_group=False)
    level = fold_level(model, unit)
    assert not level.folded
    assert level.opened is None
    keys = {box.key.kind for box in level.boxes}
    assert OverviewRefKind.GROUP not in keys
    assert {item_id("p1"), item_id("k1"), item_id("k2")} <= {_id(box.key) for box in level.boxes}
    assert len(level.boxes) > 1


def test_a_group_the_unit_does_not_hold_is_refused() -> None:
    """Opening a group id that is not one of the unit's groups raises `SchemaError`."""
    model, unit, _ = fold_plant(ctl_group=False)
    with pytest.raises(SchemaError):
        fold_level(model, unit, CTL_BOX)


def test_a_stub_names_its_far_end_as_a_reference_and_folds_per_kind() -> None:
    """`end` is the far unit for a unit fold, the far item for an end, the group for a group stub.

    Dropping `end` from `RawStub` or from the fold key leaves two far ends in one stub.
    """
    model, unit, far = fold_plant()
    level = fold_level(model, unit)
    (folded,) = [s for s in level.stubs if s.place is StubPlace.UNIT]
    assert folded.end == OverviewRef(kind=OverviewRefKind.UNIT, unit=far)
    (single,) = [s for s in level.stubs if s.place is StubPlace.END]
    assert single.end == OverviewRef(kind=OverviewRefKind.ITEM, item=item_id("b1"))
    assert single.end == single.members[0].end
    assert (single.via, folded.via) == (None, None)
    in_ctl = fold_level(model, unit, CTL_BOX)
    (to_sup,) = [
        s for s in in_ctl.stubs if s.place is StubPlace.GROUP and s.box.item == item_id("k1")
    ]
    assert to_sup.end == OverviewRef(kind=OverviewRefKind.GROUP, node=SUP)


def test_the_all_devices_view_of_a_folded_unit_opens_straight() -> None:
    """`fold=False` gives the see-through view of a unit that has two groups."""
    model, unit, _ = fold_plant()
    level = fold_level(model, unit, fold=False)
    assert not level.folded
    assert level.opened is None
    assert len(level.boxes) > len(fold_level(model, unit).boxes)


def test_a_closed_fold_prints_its_name_and_count_and_a_single_stub_keeps_its_ports() -> None:
    """O3b: the -U9 fold of two ends is its name and `x 2`; the single end -B1 keeps its ports."""
    model, unit, _ = fold_plant()
    level = fold_level(model, unit)
    closed = next(s for s in level.stubs if s.place is StubPlace.UNIT)
    single = next(s for s in level.stubs if s.place is StubPlace.END)
    assert overview_fold_stub_lines(closed) == (closed.far,)
    tails = single.members[0].ports
    assert overview_fold_stub_lines(single) == ((single.far, tails) if tails else (single.far,))
    ref = OverviewRef(kind=OverviewRefKind.ITEM, item=item_id("d1"))
    boxes, lines = stub_ends(model, unit, [(ref, closed)])
    assert boxes[0].lines == (closed.far,)
    assert lines[0].text == "x 2"


def test_a_cable_fold_counts_its_cables_and_a_wire_fold_its_wires() -> None:
    """A15: breaks if a cable line counts cores instead of cables."""
    model, unit, _ = fold_plant()
    level = fold_level(model, unit)
    closed = next(s for s in level.stubs if s.place is StubPlace.UNIT)
    ref = OverviewRef(kind=OverviewRefKind.ITEM, item=item_id("d1"))
    cab_a, cab_b = item_id("cab1"), item_id("cab2")
    members = tuple(
        dataclasses.replace(
            closed.members[0],
            kind=OverviewLinkKind.CABLE,
            via=cab_a if i < 4 else cab_b,
            count=1,
        )
        for i in range(8)
    )
    cable = dataclasses.replace(closed, kind=OverviewLinkKind.CABLE, count=8, members=members)
    _, lines = stub_ends(model, unit, [(ref, cable)])
    assert lines[0].text == "x 2"
    wire = dataclasses.replace(closed, kind=OverviewLinkKind.WIRE, count=8, members=())
    _, lines = stub_ends(model, unit, [(ref, wire)])
    assert lines[0].text == "x 8"
