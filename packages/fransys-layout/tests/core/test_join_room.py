"""Stage 5, join room (R456, layout-0381): a foot join is levelled with the jogs of its step only where its stair has no row."""

from __future__ import annotations

import pytest
from options_fixtures import core_options

from fransys_layout.core import Facts, PlacementProblem
from fransys_layout.core.pack import cell_node
from fransys_layout.core.place_room import _join_wires, step_rooms
from fransys_layout.core.place_x import place_x

from .conftest import MARKER
from .flow_builders import AREA, elem, net
from .test_place_x import env_of

G = 8
OPTIONS = core_options(
    marker=MARKER,
)


def _fold(b_below: int | None):
    """The env, x and column of the fold, and y with b's cell `b_below` lower than the solved y (None: page unsolved)."""
    syms = (elem("src", stand_n="SUPPLY"), elem("a"), elem("b"))
    nets = (net("n1", "src.s", "a.n", "b.n"), net("n2", "a.s", "b.s"))
    env = env_of(PlacementProblem(AREA, syms, nets, facts=Facts(far_ends=())), OPTIONS)
    x, _ = place_x(env)
    pc = env.pcs[env.flow.columns[0].id]
    y = None
    if b_below is not None:
        y = {cell_node(pc.id, li, i): 80 for li, cells in enumerate(pc.lanes) for i in range(len(cells))}
        y[cell_node(pc.id, 1, 0)] += b_below
    return env, x, pc, y


def _reserved(b_below: int | None) -> int:
    """The step above a's cell, b's foot join a lane apart."""
    env, x, pc, y = _fold(b_below)
    return step_rooms(env, x, y).get((pc.id, 0, 0), 0)


@pytest.mark.parametrize("apart", [0, G])
def test_a_join_level_or_one_grid_apart_reserves_its_turn_row(apart: int) -> None:
    """Pins level or one grid apart leave a stair no row: the step above the join's cell is reserved (R2287 A4)."""
    assert _reserved(apart) >= G * OPTIONS.jog_lanes


@pytest.mark.parametrize("apart", [None, 2 * G, 3 * G])
def test_a_join_unsolved_level_or_with_a_row_reserves_nothing(apart: int | None) -> None:
    """An unsolved page reserves none; pins two or more grids apart already have a row (R456)."""
    assert _reserved(apart) == 0


def test_a_join_whose_step_holds_jogs_keeps_its_wires_whatever_its_row() -> None:
    """The jogs of the step share its row with the join, so the join is levelled with them (layout-0381)."""
    env, _, pc, y = _fold(2 * G)
    assert list(_join_wires(env, pc, y, set())) == []
    assert list(_join_wires(env, pc, y, {(pc.id, 0, 0)})) != []
