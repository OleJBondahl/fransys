"""layout-0395 R535 R-A: a wire of the owner's net enters the owner's box only at its port cell.

Every footprint cell is hard for every wire; the cell of a symbol's own pin point is open to the
symbol's own net, so the net reaches its pin but never runs through the body to a point beyond.
"""

from __future__ import annotations

from dataclasses import replace

from fransys_layout.core import Box, PinRef
from fransys_layout.core.clearance import Keep
from fransys_layout.core.occupancy import Occupancy
from fransys_layout.core.outputs import PinXY, Placed
from fransys_layout.core.route import _mark_fixed
from fransys_layout.core.route_astar import Leg, astar

from .route_fixtures import link_env

STEP = 8
PIN8 = (64, 48)  # the port point in pixels
BODY = Box(64, 24, 48, 48)  # closed cells x 8..14, y 3..9
PIN = (8, 6)  # the pin on the west edge, in cells
ENV0 = link_env({"s": (64, 48, "E")}, {})
ENV = replace(
    ENV0,
    placed={"s": Placed("s", 1, 64, 48, "R0", BODY, BODY, (PinXY("p", 64, 48),))},
    net_pins={"x": (PinRef("s", "p"),)},
)


def _path(goal: tuple[int, int], own: frozenset[str]):
    grid = Occupancy(24, 12, STEP)
    _mark_fixed(ENV, grid)
    path = astar(grid, Leg("x", (1, 6), goal, own=own), ENV.options)
    return grid, path


def test_the_owners_net_reaches_its_own_pin() -> None:
    _, path = _path(PIN, frozenset({"s"}))
    assert path is not None
    assert path[-1] == PIN


def test_the_owners_net_does_not_pass_through_the_body_to_a_point_beyond() -> None:
    grid, path = _path((16, 6), frozenset({"s"}))
    assert path is not None
    assert [c for c in path if c in grid.hard] == []


def test_a_foreign_net_is_blocked_from_the_pin_cell() -> None:
    assert _path(PIN, frozenset({"t"}))[1] is None


MARK = Keep("", Box(64, 24, 48, 48), "marker", "s", "x", PIN8)  # same cells as BODY
ENV_MARK = replace(ENV0, placed={}, obstacles=(MARK,))


def _mark_path(goal: tuple[int, int], own: frozenset[str]):
    grid = Occupancy(24, 12, STEP)
    _mark_fixed(ENV_MARK, grid)
    return grid, astar(grid, Leg("x", (1, 6), goal, own=own), ENV_MARK.options)


def test_the_owners_net_reaches_its_marker_port_cell() -> None:
    assert _mark_path(PIN, frozenset({"s"}))[1][-1] == PIN


def test_the_owners_net_does_not_pass_through_its_marker_box() -> None:
    grid, path = _mark_path((16, 6), frozenset({"s"}))
    assert path is not None
    assert [c for c in path if c in grid.hard] == []


def test_a_foreign_net_is_blocked_from_the_marker_port_cell() -> None:
    assert _mark_path(PIN, frozenset({"t"}))[1] is None


PINS2 = (PinXY("p", 64, 48), PinXY("q", 64, 64))  # q: a second pin of s, on net y
ENV2 = replace(
    ENV,
    placed={"s": Placed("s", 1, 64, 48, "R0", BODY, BODY, PINS2)},
    net_pins={"x": (PinRef("s", "p"),), "y": (PinRef("s", "q"),)},
)


def test_a_wire_of_the_owner_does_not_enter_a_different_pins_cell_of_the_symbol() -> None:
    grid = Occupancy(24, 12, STEP)
    _mark_fixed(ENV2, grid)
    own = frozenset({"s"})
    assert astar(grid, Leg("x", (0, 6), (8, 6), own=own), ENV2.options) is not None
    assert astar(grid, Leg("x", (0, 8), (8, 8), own=own), ENV2.options) is None
    assert astar(grid, Leg("y", (0, 8), (8, 8), own=own), ENV2.options) is not None


def test_an_off_grid_pin_is_admitted_at_the_cell_holding_its_point() -> None:
    off = replace(ENV, placed={"s": Placed("s", 1, 64, 48, "R0", BODY, BODY, (PinXY("p", 66, 49),))})
    grid = Occupancy(24, 12, STEP)
    _mark_fixed(off, grid)
    assert grid.admitted == {(8, 6): {("s", "x")}}
