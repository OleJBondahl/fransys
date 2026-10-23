"""Stage 5, join room (R456): a foot join reserves a turn row only where its stair has none."""

from __future__ import annotations

import pytest
from options_fixtures import core_options

from fransys_layout.core import Facts, PlacementProblem
from fransys_layout.core.pack import cell_node
from fransys_layout.core.place_join_room import join_rooms
from fransys_layout.core.place_room import origins
from fransys_layout.core.place_x import place_x

from .conftest import MARKER
from .flow_builders import AREA, elem, net
from .test_place_x import env_of

G = 8
OPTIONS = core_options(
    marker=MARKER,
    flip_turn="R180",
    tag_stagger=True,
    label_gap=8,
    parallel_pitch=48,
    driver_first=True,
    arrow_sides=("E", "W"),
)


def _fold() -> PlacementProblem:
    """src over a, and b in a second lane beside them: b's foot joins a's foot, a lane apart."""
    syms = (elem("src", stand_n="SUPPLY"), elem("a"), elem("b"))
    nets = (net("n1", "src.s", "a.n", "b.n"), net("n2", "a.s", "b.s"))
    return PlacementProblem(AREA, syms, nets, facts=Facts())


def _reserved(b_below: int) -> dict:
    """join_rooms with b's cell `b_below` lower than the solved y puts it (its foot pin moves)."""
    env = env_of(_fold(), OPTIONS)
    x, _ = place_x(env)
    pc = env.pcs[env.flow.columns[0].id]
    y = {
        cell_node(pc.id, li, i): 80 for li, cells in enumerate(pc.lanes) for i in range(len(cells))
    }
    y[cell_node(pc.id, 1, 0)] += b_below
    return join_rooms(env, origins(env, x), y)


def test_a_join_one_grid_apart_reserves_its_turn_row() -> None:
    """Pins one grid apart leave a stair no row: the step above the join's cell is reserved."""
    assert _reserved(G) != {}


@pytest.mark.parametrize("apart", [0, 2 * G, 3 * G])
def test_a_join_level_or_with_a_row_reserves_nothing(apart: int) -> None:
    """Level pins are one run, and pins two or more grids apart already have a row (R456)."""
    assert _reserved(apart) == {}
