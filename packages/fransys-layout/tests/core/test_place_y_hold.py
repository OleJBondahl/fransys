"""A cell's hold is read by place_y: the gap before it grows by the hold, rounded up to the grid."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from fransys_layout.core import Facts, PlacementProblem
from fransys_layout.core.constraints import Graph
from fransys_layout.core.pack import PlacedColumn, cell_node
from fransys_layout.core.place_y import _gap, stack_constraints
from fransys_layout.core.values import Cell

from .cut_fixtures import AREA, elem
from .test_place_x import env_of

if TYPE_CHECKING:
    from fransys_layout.core.place_env import PageEnv


def _env() -> PageEnv:
    return env_of(PlacementProblem(AREA, (elem("k1", 40), elem("k2", 40)), (), Facts()))


def _pc(hold: int) -> PlacedColumn:
    cells = (Cell("k1", "R0", None, None), Cell("k2", "R0", None, None, hold=hold))
    return PlacedColumn("c:k1", (cells,), (0,), 0, flipped=False)


def test_the_gap_before_a_held_cell_grows_by_the_hold() -> None:
    env = _env()
    plain, held = _pc(0), _pc(40)
    base = _gap(env, plain.lanes[0][0], plain.lanes[0][1])
    assert _gap(env, held.lanes[0][0], held.lanes[0][1]) == base + 40


@pytest.mark.parametrize("rigid", [True, False])
def test_the_stacked_cell_stands_the_hold_lower(*, rigid: bool) -> None:
    env = _env()
    ys = {}
    for hold in (0, 40):
        g = Graph()
        pc = _pc(hold)
        g.at_least(cell_node(pc.id, 0, 0), 0)
        stack_constraints(g, pc, env, {}, rigid=rigid)
        solved = g.solve()
        assert solved is not None
        ys[hold] = solved[cell_node(pc.id, 0, 1)] - solved[cell_node(pc.id, 0, 0)]
    assert ys[40] == ys[0] + 40
