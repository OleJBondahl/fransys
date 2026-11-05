"""R324: a lane wire the router leaves out is a WARNING naming the cells."""

from __future__ import annotations

from dataclasses import replace

import pytest

from fransys_layout.core.route_wires import lane_wires

from .place_fixtures import card_with_coils
from .route_fixtures import envs_of


@pytest.mark.rule("NO-SILENT-DROP")
@pytest.mark.parametrize(
    ("pair_of", "text"),
    [
        (lambda cell: (replace(cell, bottom_pin=None), cell), "no pin facing"),
        (lambda cell: (replace(cell, bottom_pin="zz"), replace(cell, top_pin="zz")), "on no net"),
    ],
    ids=["no-facing-pin", "facing-pin-on-no-net"],
)
def test_two_cells_with_no_facing_pin_or_a_facing_pin_on_no_net_are_a_finding_naming_the_first(pair_of, text) -> None:
    env = envs_of(card_with_coils(3))[0]
    col = env.columns[0]
    lane = col.lanes[0]
    cell = lane.cells[0]
    drawn = lane_wires(env, replace(col, lanes=(replace(lane, cells=pair_of(cell)),)))
    found = [f for f in drawn.findings if f.code == "LANE_WIRE_DROPPED"]
    assert [f.subject for f in found] == [cell.sym]
    assert text in found[0].text
