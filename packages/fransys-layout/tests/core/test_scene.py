"""`outputs.scene(layout, problem, flow)` flattens a planted layout, field by field."""

import dataclasses

import pytest
from scene_fixtures import flow, layout, problem

from fransys_layout.core import outputs
from fransys_layout.core.outputs import Annotations, PinXY, Placed
from fransys_layout.core.values import Cell, Column, End, FlowGraph, Lane, PinRef

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
    assert {b.sym for b in SCENE.boxes if b.head} == {"F"}


def test_rails_are_the_nets_with_a_declared_supply():
    assert SCENE.rails == frozenset({"n3"})


def test_fill_is_the_row_span_over_the_area_per_page():
    assert SCENE.fill == (20 * 50 / 10_000, 0.0)


def test_a_marker_stands_at_the_pin_its_end_names():
    m = SCENE.markers[0]
    assert (m.net, m.kind, m.page, m.x, m.y, m.box, m.pin) == ("n1", "tag", 2, 40, 46, "A", "in")


def test_a_marker_with_no_end_is_refused():
    bare = dataclasses.replace(layout().annotations.markers[0], end=None)
    bad = dataclasses.replace(layout(), annotations=Annotations(markers=(bare,)))
    with pytest.raises(ValueError, match="names no pin"):
        outputs.scene(bad, problem(), flow())


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


def test_a_quarter_turn_is_refused_until_it_has_a_side_map():
    lay = layout()
    page = lay.placement.pages[0]
    turned: Placed = dataclasses.replace(page.placed[0], orient="R90")
    page = dataclasses.replace(page, placed=(turned, *page.placed[1:]))
    bad = dataclasses.replace(
        lay, placement=dataclasses.replace(lay.placement, pages=(page, *lay.placement.pages[1:]))
    )
    with pytest.raises(ValueError, match="R90"):
        outputs.scene(bad, problem(), flow())


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
