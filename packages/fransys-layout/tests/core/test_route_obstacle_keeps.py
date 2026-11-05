"""layout-0395 3b-4, R535 R-A: an obstacle is a keep; its hard cells hold the owner's symbol.

A wire of a symbol that owns the box may start or end in it; every other wire is kept out.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from fransys_layout.core import Box
from fransys_layout.core import occupancy as occupancy_module
from fransys_layout.core.clearance import Keep
from fransys_layout.core.occupancy import Occupancy
from fransys_layout.core.route import _mark_fixed
from fransys_layout.core.route_astar import Leg, astar

from .route_fixtures import link_env

STEP = 8
ENV = link_env({"a": (8, 8, "E"), "b": (160, 8, "W")}, {})
MARKER = Keep("", Box(64, 24, 16, 16), "marker", "a", "x", (64, 32))  # cells x 8..10, y 3..5
OTHER = Keep("", Box(80, 24, 16, 16), "marker", "b", "y", (80, 32))  # cells x 10..12, y 3..5
PORT = (8, 4)  # the marker's port cell, on the box's west edge


def _grid(*keeps: Keep) -> Occupancy:
    grid = Occupancy(24, 12, STEP)
    _mark_fixed(replace(ENV, placed={}, obstacles=keeps), grid)
    return grid


def _reach(net: str, own: frozenset[str]):
    return astar(_grid(MARKER), Leg(net, (0, 4), PORT, own=own), ENV.options)


def test_a_wire_ends_at_its_own_markers_port_cell_on_the_box_edge() -> None:
    path = _reach("x", frozenset({"a"}))
    assert path is not None
    assert path[-1] == PORT


def test_a_wire_of_another_net_is_blocked_from_that_cell() -> None:
    assert _reach("y", frozenset({"b"})) is None
    assert _reach("y", frozenset()) is None


def test_the_box_is_closed_on_its_far_edge_and_owners_union_over_one_port_cell() -> None:
    grid = _grid(MARKER._replace(port=OTHER.port), OTHER)  # both ports on cell (10, 4)
    assert grid.hard[10, 4] == frozenset()
    assert grid.admitted == {(10, 4): {("a", "x"), ("b", "y")}}
    assert grid.hard[10, 5] == frozenset()  # the shared column away from the port cell
    assert grid.hard[8, 3] == frozenset()
    assert grid.hard[12, 5] == frozenset()  # the far edge is hard


def test_occupancy_imports_no_marker_name() -> None:
    source = Path(occupancy_module.__file__).read_text()
    assert "marker" not in source.lower()
    assert "Keep" not in source
