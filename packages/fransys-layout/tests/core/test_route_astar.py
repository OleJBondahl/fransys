"""Stage 6 A*: detours, bends, blocked cells and the cost of crossing another net."""

from __future__ import annotations

from dataclasses import replace

from fransys_layout.core import Box, Options
from fransys_layout.core.occupancy import Occupancy
from fransys_layout.core.outputs import Wire
from fransys_layout.core.route_astar import Leg, astar, simplify
from fransys_layout.core.route_counts import counts

STEP = 8


def path_between(*, box: bool) -> tuple[Occupancy, tuple[tuple[int, int], ...]]:
    """A path across a 12 by 7 cell map, with a box of 4 by 3 cells in the way when asked."""
    grid = Occupancy(12, 7, STEP)
    if box:
        grid.mark_box(Box(32, 16, 32, 24))
    path = astar(grid, Leg("n", (0, 3), (11, 3)), Options())
    assert path is not None
    return grid, path


def test_astar_goes_around_a_box_with_two_bends_and_straight_without() -> None:
    grid, path = path_between(box=True)
    assert not set(path) & grid.hard
    assert counts((Wire("n", 1, simplify(path, STEP), "routed"),)).bends == 2
    grid, path = path_between(box=False)
    assert simplify(path, STEP) == ((0, 24), (88, 24))


def test_a_free_cell_may_be_entered_although_blocked() -> None:
    grid = Occupancy(5, 1, STEP)
    grid.hard.add((2, 0))
    assert astar(grid, Leg("n", (0, 0), (4, 0)), Options()) is None
    assert astar(grid, Leg("n", (0, 0), (4, 0), frozenset({(2, 0)})), Options()) is not None


def test_a_cell_of_another_net_on_the_same_axis_is_blocked() -> None:
    grid = Occupancy(5, 1, STEP)
    grid.mark_wire("other", ((16, 0), (24, 0)))
    assert astar(grid, Leg("n", (0, 0), (4, 0)), Options()) is None
    grid.remove_net("other")
    assert astar(grid, Leg("n", (0, 0), (4, 0)), Options()) is not None


def _crossing_grid() -> Occupancy:
    """A vertical wire of net x at column 5 with a gap in it at row 0, on an 11 by 7 map."""
    grid = Occupancy(11, 7, STEP)
    grid.mark_wire("x", ((40, 8), (40, 48)))
    return grid


def test_a_perpendicular_cell_costs_the_crossing_penalty() -> None:
    """With a penalty of 1 the path crosses the wire; with 1000 it detours through the gap."""
    grid = _crossing_grid()
    leg = Leg("n", (0, 3), (10, 3))
    cheap = astar(grid, leg, replace(Options(), crossing_penalty=1, bend_penalty=1))
    dear = astar(grid, leg, replace(Options(), crossing_penalty=1000, bend_penalty=1))
    assert cheap is not None
    assert dear is not None
    assert len(cheap) < len(dear)
    assert (5, 3) in cheap
    assert (5, 3) not in dear


def test_the_search_stays_on_the_map() -> None:
    grid = Occupancy(3, 3, STEP)
    assert astar(grid, Leg("n", (0, 0), (5, 0)), Options()) is None
