"""Stage 1 plants for design 7.1 and 7.2: strict xfail until the named orders land."""

from __future__ import annotations

from typing import TYPE_CHECKING

from options_fixtures import core_options

from fransys_layout.core import build_flow

from .flow_plant_fixtures import fan_in1, fan_in3, tree2, tree3

if TYPE_CHECKING:
    from fransys_layout.core.values import FlowGraph, Lane


def _lanes_holding(flow: FlowGraph, sym_id: str) -> list[Lane]:
    """Every lane, in any column, with a cell of the given symbol."""
    return [
        lane
        for column in flow.columns
        for lane in column.lanes
        if any(cell.sym == sym_id for cell in lane.cells)
    ]


def test_a_three_level_tree_draws_four_lanes_under_the_hub() -> None:
    """The hub is a box (its pins are attachments, never in a lane): the child columns carry it."""
    flow = build_flow(
        tree3(),
        core_options(
            flip_turn="R180",
            tag_stagger=True,
            label_gap=8,
            driver_first=True,
            arrow_sides=("E", "W"),
        ),
    )
    assert [len(column.lanes) for column in flow.columns] == [2, 2]
    assert len(_lanes_holding(flow, "C1")) == 2
    assert len(_lanes_holding(flow, "C2")) == 2


def test_lanes_of_a_fan_in_stand_at_the_cable_boxs_pole_dx() -> None:
    flow = build_flow(
        fan_in3(),
        core_options(
            flip_turn="R180",
            tag_stagger=True,
            label_gap=8,
            driver_first=True,
            arrow_sides=("E", "W"),
        ),
    )
    assert sorted(lane.offset for lane in _lanes_holding(flow, "K")) == [0, 16, 32]


def test_a_two_level_tree_passes() -> None:
    flow = build_flow(
        tree2(),
        core_options(
            flip_turn="R180",
            tag_stagger=True,
            label_gap=8,
            driver_first=True,
            arrow_sides=("E", "W"),
        ),
    )
    assert [len(column.lanes) for column in flow.columns] == [1, 1]
    assert len(_lanes_holding(flow, "C1")) == 1
    assert len(_lanes_holding(flow, "C2")) == 1


def test_a_fan_in_with_one_head_passes() -> None:
    flow = build_flow(
        fan_in1(),
        core_options(
            flip_turn="R180",
            tag_stagger=True,
            label_gap=8,
            driver_first=True,
            arrow_sides=("E", "W"),
        ),
    )
    lanes = _lanes_holding(flow, "K")
    assert len(lanes) == 3
    assert len({lane.offset for lane in lanes}) == 3
