"""`outputs.scene(layout, problem, flow)` flattens a planted layout, field by field."""

import dataclasses

import pytest
from scene_fixtures import flow, layout, problem

from fransys_layout.core import outputs
from fransys_layout.core.geometry import rotate_side
from fransys_layout.core.outputs import PinXY, Placed
from fransys_layout.core.values import Box, Cell, Column, End, FlowGraph, Lane, PinRef

SCENE = outputs.scene(layout(), problem(), flow())
BOXES = {b.sym: b for b in SCENE.boxes}


def _pins(sid: str) -> dict[str, outputs.ScenePin]:
    return {p.pin: p for p in BOXES[sid].pins}


def test_the_scene_carries_the_area_the_pages_and_the_wires():
    assert (SCENE.area.w, SCENE.area.h, SCENE.pages) == (100, 100, 2)
    assert [(w.net, w.page, w.points, w.lanes) for w in SCENE.wires] == [
        ("n2", 2, ((40, 14), (40, 4)), 1)
    ]
    assert [(b.sym, b.page) for b in SCENE.boxes] == [("K", 1), ("F", 1), ("A", 2), ("T", 2)]


def test_a_pin_carries_its_net_node_stand_and_box_flag():
    k, f, a = _pins("K")["c1"], _pins("F"), _pins("A")
    assert (k.net, k.node, k.box, k.stand) == ("n1", 0, True, False)
    assert (f["p"].net, f["p"].node, f["p"].stand, f["p"].box) == ("n3", 1, True, False)
    assert (a["in"].net, a["in"].x, a["in"].y) == ("n1", 40, 46)


def test_a_turned_symbol_flips_the_side_a_wire_leaves():
    assert _pins("A")["in"].side == "S"
    assert _pins("A")["out"].side == "N"
    assert _pins("F")["out"].side == "S"


def test_a_row_group_symbol_carries_its_strip():
    assert BOXES["T"].strip == "X1"
    assert BOXES["K"].strip is None


def test_a_column_hung_on_a_box_pin_marks_its_head_cell_attached():
    assert {b.sym for b in SCENE.boxes if b.attached} == {"A"}


def test_a_fan_hub_is_marked_head():
    assert {b.sym for b in SCENE.boxes if any(p.head for p in b.pins)} == {"F"}


def test_rails_are_the_nets_with_a_declared_supply():
    assert SCENE.rails == frozenset({"n3"})


def test_fill_is_the_row_span_over_the_area_per_page():
    assert SCENE.fill == (20 * 50 / 10_000, 0.0)


def test_a_marker_stands_at_the_pin_its_end_names():
    m = SCENE.markers[0]
    assert (m.net, m.kind, m.page, m.x, m.y, m.box, m.pin) == ("n1", "tag", 2, 40, 46, "A", "in")


def test_a_marker_carries_its_cell_and_the_turned_side_of_its_pin():
    m = SCENE.markers[0]
    assert m.cell == layout().annotations.markers[0].cell == "C3"
    assert m.side == rotate_side("N", "R180") == "S"


def test_a_box_carries_the_orient_it_was_placed_with():
    assert {b.sym: b.orient for b in SCENE.boxes} == {
        "K": "R0",
        "F": "R0",
        "A": "R180",
        "T": "R0",
    }


def test_a_wire_carries_its_kind():
    assert [w.kind for w in SCENE.wires] == ["riser"]


def test_labels_and_tables_are_flattened_from_the_annotations():
    assert SCENE.labels == (outputs.SceneLabel("K", 1, Box(1, 2, 3, 4), "BR"),)
    assert SCENE.tables == (outputs.SceneTable("K", 1, Box(5, 6, 7, 8), ("3C", "2:3C"), 2),)


def test_a_placed_pin_the_problem_does_not_know_is_refused():
    lay = layout()
    page = lay.placement.pages[0]
    placed = dataclasses.replace(page.placed[0], pin_xy=(PinXY("zz", 0, 0),))
    page = dataclasses.replace(page, placed=(placed, *page.placed[1:]))
    bad = dataclasses.replace(
        lay, placement=dataclasses.replace(lay.placement, pages=(page, *lay.placement.pages[1:]))
    )
    with pytest.raises(ValueError, match=r"K\.zz is not a pin"):
        outputs.scene(bad, problem(), flow())


@pytest.mark.parametrize("orient", ["R90", "MR90"])
def test_a_quarter_turn_is_scened_with_its_turned_side(orient):
    """All eight orientations have a side rule (layout-0306): the scene carries the orient."""
    lay = layout()
    page = lay.placement.pages[0]
    turned: Placed = dataclasses.replace(page.placed[0], orient=orient)
    page = dataclasses.replace(page, placed=(turned, *page.placed[1:]))
    bad = dataclasses.replace(
        lay, placement=dataclasses.replace(lay.placement, pages=(page, *lay.placement.pages[1:]))
    )
    scened = outputs.scene(bad, problem(), flow())
    assert {b.sym: b.orient for b in scened.boxes}[turned.sym] == orient


def _three_lane_flow(head: End) -> FlowGraph:
    """One column of three lanes, one cell each, hung under a box pin by `head`."""
    lanes = tuple(Lane((Cell(s, "R0", "in", "out"),), 16 * i) for i, s in enumerate("AFT"))
    column = Column("C1", lanes, (head,), (End("open"),), 32, 48)
    return dataclasses.replace(flow(), columns=(column,))


def _attached_syms(head: End) -> set[str]:
    return {
        b.sym
        for b in outputs.scene(layout(), problem(), _three_lane_flow(head)).boxes
        if b.attached
    }


def test_a_head_end_with_a_lane_marks_only_that_lanes_cell_attached():
    assert _attached_syms(End("boxpin", "n1", PinRef("K", "c1"), lane=1)) == {"F"}


@pytest.mark.xfail(
    strict=True, reason="P1.3 fills End.lane; until then a multi-lane head over-marks"
)
def test_a_multi_lane_head_end_marks_only_the_lane_on_the_pin():
    """Stage 1 writes no lane today, so every lane's cell is marked; only lane 0 hangs on K.c1."""
    assert _attached_syms(End("boxpin", "n1", PinRef("K", "c1"))) == {"A"}


@pytest.mark.parametrize(
    ("cls", "field"),
    [
        (outputs.SceneBox, "orient"),
        (outputs.SceneWire, "kind"),
        (outputs.SceneMarker, "side"),
        (outputs.Scene, "tables"),
    ],
)
def test_a_new_scene_field_has_no_default(cls, field):
    given = {f.name: None for f in dataclasses.fields(cls) if f.name != field}
    with pytest.raises(TypeError, match=field):
        cls(**given)


@pytest.mark.parametrize(
    ("orient", "side", "turned"),
    [("MR0", "E", "W"), ("MR0", "N", "N"), ("MR180", "E", "E"), ("MR180", "N", "S")],
)
def test_the_mirror_swaps_east_and_west_before_the_turn(orient, side, turned):
    assert rotate_side(side, orient) == turned
