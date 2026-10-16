"""ROUTE-FIX D: k-end trees, windows, obstacles, wanted demand, per-net crossings and rises."""

from __future__ import annotations

from dataclasses import replace
from itertools import pairwise

from fransys_layout.core import Box, Options, PinRef
from fransys_layout.core.occupancy import Occupancy, cells_between
from fransys_layout.core.outputs import Gap, Trunk, Wire
from fransys_layout.core.route import _grid, route_page, route_pages
from fransys_layout.core.route_astar import Leg, astar
from fransys_layout.core.route_counts import collinear, crossings_by_net, demand
from fransys_layout.core.route_env import route_envs
from fransys_layout.core.route_tree import rise_wire, search
from fransys_layout.core.route_trunk import trunk_wires
from fransys_layout.core.values import Attach, Fan

from .pipeline_fixtures import cut_of, placed_from
from .route_fixtures import jog_stair, link_env, row_wrap_env

STEP = 8


def _cells(wires: tuple[Wire, ...]) -> set[tuple[int, int]]:
    return {c for w in wires for a, b in pairwise(w.points) for c in cells_between(a, b, STEP)}


def test_astar_ends_on_the_nearest_target_cell() -> None:
    grid = Occupancy(12, 7, STEP)
    leg = Leg("n", (0, 3), (11, 3), targets=frozenset({(5, 0), (5, 6)}))
    path = astar(grid, leg, Options())
    assert path is not None
    assert path[-1] in {(5, 0), (5, 6)}


def test_a_window_confines_the_search_and_search_retries_on_the_whole_page() -> None:
    grid = Occupancy(12, 7, STEP)
    grid.hard.add((5, 3))
    leg = Leg("n", (0, 3), (11, 3))
    row = (0, 3, 11, 3)
    assert astar(grid, replace(leg, window=row), Options()) is None
    path = search(grid, leg, row, Options())
    assert path is not None
    assert (5, 3) not in path


def test_crossings_by_net_counts_a_crossing_for_both_its_nets() -> None:
    wires = (
        Wire("a", 1, ((0, 8), (16, 8)), "routed"),
        Wire("b", 1, ((8, 0), (8, 16)), "routed"),
        Wire("c", 1, ((4, 0), (4, 16)), "routed"),
    )
    assert dict(crossings_by_net(wires)) == {"a": 2, "b": 1, "c": 1}


def test_a_three_end_tree_is_one_connected_set_of_routed_wires() -> None:
    from .route_fixtures import three_end_env

    wires = route_page(three_end_env())[0].wires
    assert len(wires) == 2
    assert all(w.net == "t" for w in wires)


def test_route_pages_obstacles_keep_every_wire_cell_out_of_the_boxes() -> None:
    env = link_env({"a": (40, 40, "E"), "b": (120, 40, "W")}, {"x": ("a", "b")})
    box = Box(64, 24, 16, 32)
    free, held = route_page(env)[0].wires, route_page(replace(env, obstacles=(box,)))[0].wires
    inside = {(i, j) for i in range(8, 10) for j in range(3, 7)}
    assert _cells(free) & inside
    assert not _cells(held) & inside


def test_route_envs_carry_the_obstacles_of_route_pages() -> None:
    prob = jog_stair()
    cut = cut_of(prob)
    placement = placed_from(cut, prob, Options())
    box = Box(0, 0, 8, 8)
    assert all(e.obstacles == (box,) for e in route_envs(placement, cut, prob, Options(), (box,)))
    assert route_pages(placement, cut, prob, Options()) == route_pages(
        placement, cut, prob, Options(), ()
    )


def test_demand_is_read_from_the_footprint_only_routes() -> None:
    """Two links whose verticals both want the gap count 2 tracks, though the final routes use 1."""
    pins = {"a1": (32, 64, "E"), "a2": (40, 40, "E"), "b1": (64, 88, "W"), "b2": (88, 104, "W")}
    env = link_env(pins, {"n1": ("a1", "b1"), "n2": ("a2", "b2")})
    gap = Gap("g", 1, "L", "R", 36, 64, 1)
    env = replace(env, gaps=(gap,), bands=((0, 120),))
    page, _, findings = route_page(env)
    assert page.demand[0].tracks == 2
    assert demand(page.wires, env.gaps)[0].tracks == 1  # kills: demand read from final routes
    assert [f for f in findings if f.code == "ROUTE_FAILED"] == []
    widened = replace(env, gaps=(replace(gap, tracks=page.demand[0].tracks),))
    assert collinear(route_page(widened)[0].wires) == 0


def _rise_env():
    env = link_env({"p": (40, 16, "S"), "f": (40, 40, "N")}, {})
    fan = Fan("f1", ("n",), (Attach(None, 0, 0, PinRef("p", "p")),), (), None, 1, "S")
    trunk = Trunk("f1", 1, 72, 24, 80, 1, 0)
    return replace(env, fans={"f1": fan}, trunks=(trunk,), bands=((0, 96),)), trunk


def test_a_drop_through_a_foreign_body_becomes_a_rise_routed_around_it() -> None:
    env, trunk = _rise_env()
    drawn = trunk_wires(env, trunk)
    assert len(drawn.rises) == 1
    wire = rise_wire(env, _grid(env, drawn.wires), drawn.rises[0])
    assert wire is not None
    assert wire.points[0] == (40, 16)
    assert wire.points[-1] == (40, 72)
    assert not _cells((wire,)) & _cells_of_box(env.placed["f"].footprint)


def _cells_of_box(box: Box) -> set[tuple[int, int]]:
    return {
        (i, j)
        for i in range(box.x // STEP, -(-(box.x + box.w) // STEP))
        for j in range(box.y // STEP, -(-(box.y + box.h) // STEP))
    }


def test_wanted_demand_is_what_the_links_want_alone_not_what_the_second_route_left() -> None:
    """Both links want column 48 alone; the second detours to 40 once the first holds 48."""
    pins = {"a1": (40, 24, "E"), "a2": (40, 40, "E"), "b1": (56, 56, "W"), "b2": (56, 72, "W")}
    env = link_env(pins, {"n1": ("a1", "b1"), "n2": ("a2", "b2")})
    env = replace(env, gaps=(Gap("g", 1, "L", "R", 36, 60, 1),), bands=((0, 120),))
    page = route_page(env)[0]
    assert page.demand[0].tracks == 1
    assert demand(page.wires, env.gaps)[0].tracks == 2


def test_a_rise_that_finds_no_path_is_a_finding_and_draws_no_wire() -> None:
    env, trunk = _rise_env()
    env = replace(env, obstacles=(Box(24, 56, 32, 32),))
    drawn = trunk_wires(env, trunk)
    assert rise_wire(env, _grid(env, drawn.wires), drawn.rises[0]) is None
    page, nets, findings = route_page(env)
    lost = [f for f in findings if f.code == "ROUTE_FAILED" and "p" in f.text]
    assert len(lost) == 1
    assert nets.count("n") == 1
    assert not any(w.net == "n" and w.kind == drawn.rises[0].drawn_as for w in page.wires)


def test_a_row_wrapped_fan_with_a_trunk_is_not_also_a_routed_link() -> None:
    env = row_wrap_env()
    assert any(w.kind == "routed" for w in route_page(env)[0].wires)
    trunked = replace(env, trunks=(Trunk("f:x", 1, 72, 40, 104, 1, 0),))
    assert not any(w.kind == "routed" for w in route_page(trunked)[0].wires)
