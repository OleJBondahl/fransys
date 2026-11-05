"""ROUTE-FIX D: k-end trees, windows, obstacles, wanted demand, per-net crossings and rises."""

from __future__ import annotations

from dataclasses import replace
from itertools import pairwise

from options_fixtures import core_options

from fransys_layout.core import Box, PinRef
from fransys_layout.core.clearance import Keep
from fransys_layout.core.flow_values import Attach, Fan
from fransys_layout.core.occupancy import Occupancy, cells_between
from fransys_layout.core.outputs import Gap, Refused, Trunk, Wire
from fransys_layout.core.route import _grid, route_page, route_pages
from fransys_layout.core.route_astar import Leg, astar
from fransys_layout.core.route_counts import collinear, demand
from fransys_layout.core.route_env import route_envs
from fransys_layout.core.route_tree import rise_wire
from fransys_layout.core.route_trunk import trunk_wires

from .pipeline_fixtures import cut_of, placed_from
from .route_fixtures import jog_stair, link_env, row_wrap_env

STEP = 8


def _cells(wires: tuple[Wire, ...]) -> set[tuple[int, int]]:
    return {c for w in wires for a, b in pairwise(w.points) for c in cells_between(a, b, STEP)}


def test_astar_ends_on_the_nearest_target_cell() -> None:
    grid = Occupancy(12, 7, STEP)
    leg = Leg("n", (0, 3), (11, 3), targets=frozenset({(5, 0), (5, 6)}))
    path = astar(
        grid,
        leg,
        core_options(),
    )
    assert path is not None
    assert path[-1] in {(5, 0), (5, 6)}


def test_a_three_end_tree_is_one_connected_set_of_routed_wires() -> None:
    from .route_fixtures import three_end_env

    wires = route_page(three_end_env())[0].wires
    assert len(wires) == 2
    assert all(w.net == "t" for w in wires)


def test_route_pages_obstacles_keep_every_wire_cell_out_of_the_boxes() -> None:
    env = link_env({"a": (40, 40, "E"), "b": (120, 40, "W")}, {"x": ("a", "b")})
    box = Box(64, 24, 16, 32)
    free, held = (
        route_page(env)[0].wires,
        route_page(replace(env, obstacles=(Keep("", box, "marker", "M"),)))[0].wires,
    )
    inside = {(i, j) for i in range(8, 10) for j in range(3, 7)}
    assert _cells(free) & inside
    assert not _cells(held) & inside


def test_route_envs_carry_the_obstacles_of_route_pages() -> None:
    prob = jog_stair()
    cut = cut_of(prob)
    placement = placed_from(
        cut,
        prob,
        core_options(),
    )
    keep = Keep("", Box(0, 0, 8, 8), "marker", "M")
    assert all(
        e.obstacles == (keep,)
        for e in route_envs(
            placement,
            cut,
            prob,
            core_options(),
            (keep,),
        )
    )
    assert route_pages(
        placement,
        cut,
        prob,
        core_options(),
    ) == route_pages(
        placement,
        cut,
        prob,
        core_options(),
    )


def test_demand_is_read_from_the_footprint_only_routes() -> None:
    """Two links whose verticals both want the gap count 2 tracks, though the final routes use 1."""
    pins = {"a1": (32, 64, "E"), "a2": (40, 40, "E"), "b1": (64, 88, "W"), "b2": (88, 104, "W")}
    env = link_env(pins, {"n1": ("a1", "b1"), "n2": ("a2", "b2")})
    gap = Gap("g", 1, "L", "R", 36, 64, 1)
    env = replace(env, gaps=(gap,), bands=((0, 120),))
    page, _, _ = route_page(env)
    assert page.demand[0].tracks == 2
    assert demand(page.wires, env.gaps)[0].tracks == 1  # kills: demand read from final routes
    widened = replace(env, gaps=(replace(gap, tracks=page.demand[0].tracks),))
    assert collinear(route_page(widened)[0].wires) == 0


def _rise_env():
    env = link_env({"p": (40, 16, "S"), "f": (40, 40, "N")}, {})
    fan = Fan("f1", ("n",), (Attach(None, 0, 0, PinRef("p", "p"), net="n"),), (), None, 1, "S")
    trunk = Trunk("f1", 1, 72, 24, 80, 1, 0, ((24, 80),))
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
    return {(i, j) for i in range(box.x // STEP, -(-(box.x + box.w) // STEP)) for j in range(box.y // STEP, -(-(box.y + box.h) // STEP))}


def test_wanted_demand_is_what_the_links_want_alone_not_what_the_second_route_left() -> None:
    """Both links want column 48 alone, so two nets want one column: 2 tracks (R391); the second then detours to 72."""
    pins = {"a1": (40, 24, "E"), "a2": (40, 16, "E"), "b1": (56, 56, "W"), "b2": (56, 72, "W")}
    env = link_env(pins, {"n1": ("a1", "b1"), "n2": ("a2", "b2")})
    env = replace(env, gaps=(Gap("g", 1, "L", "R", 36, 76, 1),), bands=((0, 120),))
    page = route_page(env)[0]
    assert page.demand[0].tracks == 2
    assert demand(page.wires, env.gaps)[0].tracks == 2  # the detour to 72 keeps two columns


def test_a_rise_that_finds_no_path_is_lost_and_draws_no_wire() -> None:
    env, trunk = _rise_env()
    env = replace(env, obstacles=(Keep("", Box(24, 56, 32, 32), "marker", "M"),))
    drawn = trunk_wires(env, trunk)
    assert rise_wire(env, _grid(env, drawn.wires), drawn.rises[0]) is None
    page, nets, findings = route_page(env)
    assert findings == ()
    assert nets == (Refused("n", (PinRef("p", "p"),)),)
    assert not any(w.net == "n" and w.kind == drawn.rises[0].drawn_as for w in page.wires)


def test_a_row_wrapped_fan_with_a_trunk_is_not_also_a_routed_link() -> None:
    env = row_wrap_env()
    assert any(w.kind == "routed" for w in route_page(env)[0].wires)
    trunked = replace(env, trunks=(Trunk("f:x", 1, 72, 40, 104, 1, 0, ((40, 104),)),))
    assert not any(w.kind == "routed" for w in route_page(trunked)[0].wires)


def _own_coil(box: Box):
    """The rise env with f out of the way and p's own body and footprint set to `box`."""
    env, trunk = _rise_env()
    p = env.placed["p"]
    placed = {"p": replace(p, body=box, footprint=box), "f": replace(env.placed["f"])}
    far = Box(200, 200, 8, 8)
    placed["f"] = replace(placed["f"], body=far, footprint=far)
    return replace(env, placed=placed), trunk


def test_a_drop_crossing_its_own_coil_to_a_far_pin_is_a_rise() -> None:
    """R534: the own exemption is the pin point; a drop through the coil it leaves is a hit."""
    env, trunk = _own_coil(Box(32, 8, 16, 40))
    assert len(trunk_wires(env, trunk).rises) == 1


def test_a_drop_ending_on_its_own_pin_at_the_body_edge_is_straight() -> None:
    """R534: a drop leaving its pin on the body edge touches the body in that point only."""
    env, trunk = _own_coil(Box(32, 8, 16, 8))
    drawn = trunk_wires(env, trunk)
    assert drawn.rises == ()
    assert [w.points for w in drawn.wires if w.kind != "trunk"] == [((40, 16), (40, 72))]


def test_a_standing_label_closes_its_interior_to_the_router_and_its_sides_stay_open() -> None:
    """T2: the router's grid holds each label as a keep; touching a label's side is clear, as it is for the label."""
    env, _ = _rise_env()
    box = Box(64, 40, 24, 16)
    inner = Box(box.x + STEP, box.y + STEP, STEP, STEP)
    assert _grid(env, ()).free(inner)
    grid = _grid(env, (), (Keep("", box, "text", "S1:text"),))
    assert not grid.free(inner)
    assert grid.free(Box(box.x - STEP, box.y, STEP, STEP))
