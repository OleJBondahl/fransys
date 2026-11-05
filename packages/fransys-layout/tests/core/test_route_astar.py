"""Stage 6 A*: detours, bends, blocked cells and the cost of crossing another net."""

from __future__ import annotations

from dataclasses import replace

import pytest
from options_fixtures import core_options

from fransys_layout.core import Box
from fransys_layout.core.occupancy import Occupancy
from fransys_layout.core.outputs import Wire
from fransys_layout.core.route_astar import Leg, astar, simplify
from fransys_layout.core.route_counts import counts

STEP = 8
OPTIONS = core_options()


def path_between(*, box: bool) -> tuple[Occupancy, tuple[tuple[int, int], ...]]:
    """A path across a 12 by 7 cell map, with a box of 4 by 3 cells in the way when asked."""
    grid = Occupancy(12, 7, STEP)
    if box:
        grid.mark_box(Box(32, 16, 32, 24))
    path = astar(
        grid,
        Leg("n", (0, 3), (11, 3)),
        OPTIONS,
    )
    assert path is not None
    return grid, path


def test_astar_goes_around_a_box_with_two_bends_and_straight_without() -> None:
    grid, path = path_between(box=True)
    assert not set(path) & grid.hard.keys()
    assert counts((Wire("n", 1, simplify(path, STEP), "routed"),)).bends == 2
    grid, path = path_between(box=False)
    assert simplify(path, STEP) == ((0, 24), (88, 24))


def test_a_free_cell_may_be_entered_although_blocked() -> None:
    grid = Occupancy(5, 1, STEP)
    grid.hard[2, 0] = frozenset()
    assert (
        astar(
            grid,
            Leg("n", (0, 0), (4, 0)),
            OPTIONS,
        )
        is None
    )
    assert (
        astar(
            grid,
            Leg("n", (0, 0), (4, 0), frozenset({(2, 0)})),
            OPTIONS,
        )
        is not None
    )


def test_a_cell_of_another_net_on_the_same_axis_is_blocked() -> None:
    grid = Occupancy(5, 1, STEP)
    grid.mark_wire("other", ((16, 0), (24, 0)))
    assert (
        astar(
            grid,
            Leg("n", (0, 0), (4, 0)),
            OPTIONS,
        )
        is None
    )
    grid.remove_net("other")
    assert (
        astar(
            grid,
            Leg("n", (0, 0), (4, 0)),
            OPTIONS,
        )
        is not None
    )


def _crossing_grid() -> Occupancy:
    """A vertical wire of net x at column 5 with a gap in it at row 0, on an 11 by 7 map."""
    grid = Occupancy(11, 7, STEP)
    grid.mark_wire("x", ((40, 8), (40, 48)))
    return grid


def test_a_perpendicular_cell_costs_the_crossing_penalty() -> None:
    """With a penalty of 1 the path crosses the wire; with 1000 it detours through the gap."""
    grid = _crossing_grid()
    leg = Leg("n", (0, 3), (10, 3))
    cheap = astar(
        grid,
        leg,
        replace(
            OPTIONS,
            crossing_penalty=1,
            bend_penalty=1,
        ),
    )
    dear = astar(
        grid,
        leg,
        replace(
            OPTIONS,
            crossing_penalty=1000,
            bend_penalty=1,
        ),
    )
    assert cheap is not None
    assert dear is not None
    assert len(cheap) < len(dear)
    assert (5, 3) in cheap
    assert (5, 3) not in dear


def test_the_search_stays_on_the_map() -> None:
    grid = Occupancy(3, 3, STEP)
    assert (
        astar(
            grid,
            Leg("n", (0, 0), (5, 0)),
            OPTIONS,
        )
        is None
    )


def test_history_on_a_cell_moves_the_path_to_the_cheaper_detour() -> None:
    """With no history the path is straight; history on one of its cells sends it round."""
    _, straight = path_between(box=False)
    assert simplify(straight, STEP) == ((0, 24), (88, 24))
    grid = Occupancy(12, 7, STEP)
    grid.add_history((5, 3), "h", 1000)
    path = astar(
        grid,
        Leg("n", (0, 3), (11, 3)),
        OPTIONS,
    )
    assert path is not None
    assert (5, 3) not in path


def _shared_row(share_cost: int, rows: int) -> tuple[tuple[int, int], ...] | None:
    """A path from (0, 0) to (4, 0) past another net's horizontal run on cell (2, 0)."""
    grid = Occupancy(5, rows, STEP)
    grid.used[2, 0] = [("x", "h")]
    grid.share_cost = share_cost
    return astar(grid, Leg("n", (0, 0), (4, 0)), OPTIONS)


def test_a_hard_cell_is_not_shared_and_a_soft_one_is_shared_at_its_price() -> None:
    assert _shared_row(0, 1) is None
    assert _shared_row(10, 1) == ((0, 0), (1, 0), (2, 0), (3, 0), (4, 0))


def test_a_soft_share_detours_when_the_detour_is_cheaper_than_the_price() -> None:
    cheap, dear = _shared_row(1, 2), _shared_row(10_000, 2)
    assert cheap is not None
    assert (2, 0) in cheap
    assert dear is not None
    assert (2, 0) not in dear


def test_a_soft_round_turns_on_another_nets_wire_and_a_hard_one_does_not() -> None:
    def run(share_cost: int) -> tuple[tuple[int, int], ...] | None:
        grid = Occupancy(3, 2, STEP)
        grid.hard[1, 1] = frozenset()
        grid.used[2, 0] = [("x", "v")]
        grid.share_cost = share_cost
        return astar(grid, Leg("n", (0, 0), (2, 1)), OPTIONS)

    assert run(0) is None
    assert run(1) == ((0, 0), (1, 0), (2, 0), (2, 1))


@pytest.mark.rule("ROUTING")
@pytest.mark.parametrize(("goal", "bend", "cross"), [((6, 2), 1, 34), ((6, 2), 9, 50), ((6, 2), 19, 70), ((6, 3), 1, 17), ((6, 3), 9, 25)])
def test_at_an_exact_tie_the_path_with_fewer_crossings_wins(goal: tuple[int, int], bend: int, cross: int) -> None:
    """The crossing price equals the detour over the wire's end: the path that crosses nothing wins (R643)."""
    grid = Occupancy(8, 6, STEP)
    grid.mark_wire("o", [(24, 8), (24, 24)])
    options = replace(
        OPTIONS,
        crossing_penalty=cross,
        bend_penalty=bend,
    )
    path = astar(grid, Leg("n", (0, 2), goal), options)
    assert path is not None
    assert sum(grid.crossing(c, "h", "n") for c in path) == 0
