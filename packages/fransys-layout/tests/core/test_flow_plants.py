"""Stage 1 plants for design 7.1 and 7.2: strict xfail until the named orders land."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from options_fixtures import core_options

from fransys_layout.core import build_flow

from .flow_plant_fixtures import fan_in1, fan_in3, tree2, tree3
from .pipeline_fixtures import solved_of

if TYPE_CHECKING:
    from fransys_layout.core.flow_values import FlowGraph, Lane


def _lanes_holding(flow: FlowGraph, sym_id: str) -> list[Lane]:
    """Every lane, in any column, with a cell of the given symbol."""
    return [lane for column in flow.columns for lane in column.lanes if any(cell.sym == sym_id for cell in lane.cells)]


@pytest.mark.parametrize(("one_leaf", "lanes"), [(False, [1, 1, 1, 1]), (True, [1, 1])])
def test_a_hub_dealt_twice_stands_once_in_the_tree(*, one_leaf: bool, lanes: list[int]) -> None:
    """G03-CIRCUIT-TREE: each symbol stands once in the tree; a child with two leaves is one lane, its net a fan."""
    flow = build_flow(
        tree3(one_leaf=one_leaf),
        core_options(),
    )
    assert [len(column.lanes) for column in flow.columns] == lanes
    assert len(_lanes_holding(flow, "C1")) == len(_lanes_holding(flow, "C2")) == 1


def test_lanes_of_a_fan_in_stand_at_the_cable_boxs_pole_dx() -> None:
    flow = build_flow(
        fan_in3(),
        core_options(),
    )
    assert sorted(lane.offset for lane in _lanes_holding(flow, "K")) == [0, 16, 32]


def test_a_two_level_tree_passes() -> None:
    flow = build_flow(
        tree2(),
        core_options(),
    )
    assert [len(column.lanes) for column in flow.columns] == [1, 1]
    assert [len(_lanes_holding(flow, s)) for s in ("C1", "C2")] == [1, 1]
    assert [(e.kind, e.lane) for c in flow.columns for e in c.heads] == [("boxpin", 0), ("boxpin", 0)]


def test_a_fan_in_with_one_head_passes() -> None:
    flow = build_flow(
        fan_in1(),
        core_options(),
    )
    lanes = _lanes_holding(flow, "K")
    assert len(lanes) == 3
    assert len({lane.offset for lane in lanes}) == 3


def test_the_legs_of_a_hub_stand_beside_their_hub() -> None:
    """KI-216: C1's leaves G1 and G2 stand before C2's G3 and G4, so no wire runs under a neighbour's drop."""
    placed = solved_of(tree3()).placement.pages[0].placed
    assert [p.sym for p in sorted(placed, key=lambda p: p.x) if p.sym.startswith("G")] == ["G1", "G2", "G3", "G4"]
