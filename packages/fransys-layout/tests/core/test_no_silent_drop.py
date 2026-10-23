"""R324: a lane wire the router leaves out is a WARNING naming the cells."""

from __future__ import annotations

from dataclasses import replace

import pytest

from fransys_layout.core.route_wires import lane_wires

from .place_fixtures import card_with_coils
from .route_fixtures import envs_of


@pytest.mark.rule("NO-SILENT-DROP")
def test_two_cells_with_no_facing_pin_are_a_finding_naming_the_first() -> None:
    env = envs_of(card_with_coils(3))[0]
    col = env.columns[0]
    lane = col.lanes[0]
    cell = lane.cells[0]
    pair = (replace(cell, bottom_pin=None), cell)
    drawn = lane_wires(env, replace(col, lanes=(replace(lane, cells=pair),)))
    found = [f for f in drawn.findings if f.code == "LANE_WIRE_DROPPED"]
    assert [f.subject for f in found] == [cell.sym]
    assert "no pin facing" in found[0].text


@pytest.mark.rule("NO-SILENT-DROP")
def test_two_cells_with_a_facing_pin_on_no_net_are_a_finding() -> None:
    env = envs_of(card_with_coils(3))[0]
    col = env.columns[0]
    lane = col.lanes[0]
    cell = lane.cells[0]
    pair = (replace(cell, bottom_pin="zz"), replace(cell, top_pin="zz"))
    drawn = lane_wires(env, replace(col, lanes=(replace(lane, cells=pair),)))
    found = [f for f in drawn.findings if f.code == "LANE_WIRE_DROPPED"]
    assert [f.subject for f in found] == [cell.sym]
    assert "on no net" in found[0].text
