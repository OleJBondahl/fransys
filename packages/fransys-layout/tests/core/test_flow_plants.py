"""Stage 1 plants for design 7.1 and 7.2: strict xfail until the named orders land."""

from __future__ import annotations

import pytest

from fransys_layout.core import build_flow
from fransys_layout.core.values import FlowGraph, Lane, Options

from .flow_plant_fixtures import fan_in1, fan_in3, tree2, tree3


def _lanes_holding(flow: FlowGraph, sym_id: str) -> list[Lane]:
    """Every lane, in any column, with a cell of the given symbol."""
    return [
        lane
        for column in flow.columns
        for lane in column.lanes
        if any(cell.sym == sym_id for cell in lane.cells)
    ]


@pytest.mark.xfail(
    strict=True,
    reason=(
        "stage 1 folds one level of branching; a lane that splits again at depth two is not "
        "read (design 7.1); P7.8's order removes this marker or the builder cuts at depth two "
        "with a cross-link"
    ),
)
def test_a_three_level_tree_draws_four_lanes_under_the_hub() -> None:
    """The hub is a box (its pins are attachments, never in a lane): the child columns carry it."""
    flow = build_flow(tree3(), Options())
    assert [len(column.lanes) for column in flow.columns] == [2, 2]
    assert len(_lanes_holding(flow, "C1")) == 2
    assert len(_lanes_holding(flow, "C2")) == 2


@pytest.mark.xfail(
    strict=True,
    reason=(
        "the lane table is the pin dx of the first shared symbol by natural key (the foot B1), "
        "not the cable box K "
        "(design 7.2); P7.9's order removes this marker"
    ),
)
def test_lanes_of_a_fan_in_stand_at_the_cable_boxs_pole_dx() -> None:
    flow = build_flow(fan_in3(), Options())
    assert sorted(lane.offset for lane in _lanes_holding(flow, "K")) == [0, 16, 32]


def test_a_two_level_tree_passes() -> None:
    flow = build_flow(tree2(), Options())
    assert [len(column.lanes) for column in flow.columns] == [1, 1]
    assert len(_lanes_holding(flow, "C1")) == 1
    assert len(_lanes_holding(flow, "C2")) == 1


def test_a_fan_in_with_one_head_passes() -> None:
    flow = build_flow(fan_in1(), Options())
    lanes = _lanes_holding(flow, "K")
    assert len(lanes) == 3
    assert len({lane.offset for lane in lanes}) == 3
