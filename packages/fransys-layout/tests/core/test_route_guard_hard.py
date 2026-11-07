"""TRUNK-CLEAR item 3b (layout-0394): the guard reroutes a fixed wire that crosses a hard box.

No other net stands anywhere: only a footprint (or an obstacle) is crossed, which the net marks
of the grid never show. A wire ending in its own symbol's footprint is not a crossing.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from fransys_layout.core import Box, PinRef
from fransys_layout.core.clearance import Keep, own_end
from fransys_layout.core.flow_values import Attach, Fan
from fransys_layout.core.occupancy import Occupancy
from fransys_layout.core.outputs import PinXY, Placed, Refused, Wire
from fransys_layout.core.route_env import Drawn, hard_keeps
from fransys_layout.core.route_guard import _meets, guard

from .route_fixtures import link_env
from .test_route_guard_off_grid import X, _env_and_grid

ACROSS = Wire("n", 1, ((496, 112), (776, 112)), "straight")  # through B's footprint (588..704)


def _crossed(env, grid, wire=ACROSS) -> Wire:
    return guard(env, grid, Drawn(wires=(wire,))).wires[0]


def _inside_footprint(w: Wire, box: Box) -> bool:
    return any(
        min(ax, bx) < box.x + box.w and max(ax, bx) > box.x and min(ay, by) < box.y + box.h and max(ay, by) > box.y
        for (ax, ay), (bx, by) in zip(w.points, w.points[1:], strict=False)
    )


def test_a_fixed_wire_through_a_foreign_footprint_is_rerouted() -> None:
    env, grid, (box_fp, _) = _env_and_grid()
    wire = _crossed(env, grid)
    assert wire.kind == "routed"
    assert wire.points[0] == (496, 112)
    assert wire.points[-1] == (776, 112)
    assert not _inside_footprint(wire, box_fp)


def _marker_env():
    env, grid, _ = _env_and_grid()
    marker = Box(300, 100, 48, 24)
    env = replace(env, placed={}, obstacles=(Keep("", marker, "marker", "M"),))
    grid.hard.clear()
    grid.mark_box(marker)
    return env, grid


def test_a_wire_through_an_obstacle_stays_as_drawn() -> None:
    """R535 R-B: a fixed wire meeting a marker keep is never rerouted; el counts it instead."""
    env, grid = _marker_env()
    through = Wire("n", 1, ((256, 112), (400, 112)), "straight")
    assert _crossed(env, grid, through).kind == "straight"


@pytest.mark.parametrize(
    ("kind", "points"),
    [
        ("trunk", ((256, 112), (400, 112))),
        ("straight", ((256, 112), (400, 112))),
        ("join", ((256, 112), (400, 112))),
        ("drop", ((320, 80), (320, 160))),
        ("riser", ((320, 80), (320, 160))),
    ],
)
def test_a_fixed_wire_through_a_marker_keep_is_returned_unchanged(kind, points) -> None:
    env, grid = _marker_env()
    wire = Wire("n", 1, points, kind)
    drawn = guard(env, grid, Drawn(wires=(wire,)))
    assert drawn.wires == (wire,)
    assert not drawn.findings


def test_a_wire_ending_at_its_own_markers_port_is_unchanged_and_unflagged() -> None:
    """The marker sits in B's footprint; the wire ends at its port, in B's own box."""
    env, grid, _ = _env_and_grid()
    marker = Keep("", Box(600, 100, 40, 24), "marker", "B", "n")
    env = replace(env, net_pins={"n": (PinRef("B", "1"),)}, obstacles=(marker,))
    wire = Wire("n", 1, ((496, 112), (620, 112)), "straight")
    assert own_end((620, 112), wire.points[-1])
    drawn = guard(env, grid, Drawn(wires=(wire,)))
    assert drawn.wires == (wire,)
    assert not drawn.findings


def test_a_wire_of_the_symbols_own_net_may_stand_in_its_footprint() -> None:
    env, grid, _ = _env_and_grid()
    env = replace(env, net_pins={"n": (PinRef("B", "1"),)})
    inside = Wire("n", 1, ((X, 96), (X, 128)), "straight")
    assert _crossed(env, grid, inside).kind == "straight"


def test_a_wire_along_a_footprint_edge_is_not_a_crossing() -> None:
    env, grid, (box_fp, _) = _env_and_grid()
    edge = Wire("n", 1, ((box_fp.x + box_fp.w, 40), (box_fp.x + box_fp.w, 90)), "straight")
    assert _crossed(env, grid, edge).kind == "straight"


def test_the_route_grid_closes_an_obstacle_and_a_footprint_on_the_far_edge() -> None:
    """R535 R-C: an obstacle (a marker box) and a footprint are closed (layout-0395 R-A)."""
    from fransys_layout.core.occupancy import Occupancy
    from fransys_layout.core.route import _mark_fixed

    env, _, (box_fp, _) = _env_and_grid()
    marker = Box(800, 96, 16, 16)  # x 800..816, y 96..112, edges on the 8 grid
    env = replace(env, obstacles=(Keep("", marker, "marker", "M"),))
    grid = Occupancy(120, 40, 8)
    _mark_fixed(env, grid)
    assert grid.blocked((102, 12), "h", "n"), "marker far edge column"
    assert grid.blocked((101, 14), "v", "n"), "marker far edge row"
    assert (box_fp.x + box_fp.w) % 8 == 0
    assert grid.blocked(((box_fp.x + box_fp.w) // 8, 13), "h", "n"), "footprint far edge"


def test_a_bundle_lane_through_a_symbol_of_its_fan_stays_as_drawn() -> None:
    """R515 R-A: the symbols of the fan a lane belongs to are its own, though the lane's net has no pin there."""
    from fransys_layout.core.flow_values import Attach, Fan

    env, grid, _ = _env_and_grid()
    fan = Fan("f:m", ("m1", "m2"), (Attach(None, 0, 0, PinRef("B", "1"), net="m1"),), (), None, 2, "below")
    lane = Wire("m1", 1, ((496, 112), (776, 112)), "trunk")
    own = replace(env, fans={"f:m": fan}, net_pins={"m1": (PinRef("P", "in"),)})
    assert _crossed(own, grid, lane).kind == "trunk"
    assert not _meets(own, grid, lane, "m1", (frozenset(), hard_keeps(own)))
    assert _meets(replace(own, fans={}), grid, lane, "m1", (frozenset(), hard_keeps(replace(own, fans={}))))


def test_a_wire_through_a_neighbours_tag_room_stays_as_drawn() -> None:
    """layout-0495: B's footprint holds soft tag room over the wire's column; its body does not."""
    env, grid, (box_fp, _) = _env_and_grid()
    body = Box(box_fp.x + box_fp.w - 8, box_fp.y, 8, box_fp.h)
    placed = {"B": replace(env.placed["B"], body=body)}
    env = replace(env, placed=placed, net_pins={})
    wire = Wire("n", 1, ((624, 80), (624, 132)), "straight")
    drawn = guard(env, grid, Drawn(wires=(wire,)))
    assert drawn.wires == (wire,)
    assert not drawn.findings


def _trunk_of_three(*, wall: bool):
    """A trunk at y 136 from pin A (200) to pin C (400) with pin B (216) tapping inside; a foreign box F stands on it (KI-731)."""
    env = link_env({"A": (200, 100, "N"), "B": (216, 100, "N"), "C": (400, 100, "N")}, {})
    f_box = Box(280, 128, 48, 24)
    placed = {**env.placed, "F": Placed("F", 1, 280, 152, "R0", f_box, f_box, (PinXY("p", 280, 152),))}
    att = [Attach(None, 0, 0, PinRef(s, "p"), net="n") for s in "ABC"]
    fan = Fan("f:n", ("n",), tuple(att[:2]), (att[2],), None, 1, "below")
    env = replace(env, placed=placed, fans={"f:n": fan})
    grid = Occupancy(100, 40, 8)
    for p in placed.values():
        grid.mark_box(p.footprint)
    if wall:
        grid.mark_box(Box(336, 0, 8, 320))
    taps = tuple(Wire("n", 1, ((x, 100), (x, 136)), "drop") for x in (200, 216, 400))
    return env, grid, Drawn(wires=(Wire("n", 1, ((200, 136), (400, 136)), "trunk"), *taps))


def test_a_met_trunk_is_rerouted_as_one_tree_over_all_its_taps() -> None:
    """KI-731: the inner tap is not dropped; the first-to-last reroute left it on nothing."""
    env, grid, drawn = _trunk_of_three(wall=False)
    out = guard(env, grid, drawn)
    joined = [w for w in out.wires if w.points[0] == (216, 136) and w.points[-1] != (216, 100)]
    assert joined, [w.points for w in out.wires]
    assert any((200, 136) in (w.points[0], w.points[-1]) and (400, 136) in (w.points[0], w.points[-1]) for w in out.wires)
    assert out.lost == ()


def test_a_met_trunk_with_no_tree_hands_every_tap_to_the_reference_loop() -> None:
    """KI-731: no way for the tree keeps no wire that meets the foreign box; the taps become one Refused."""
    env, grid, drawn = _trunk_of_three(wall=True)
    out = guard(env, grid, drawn)
    assert out.wires == ()
    assert out.lost == (Refused("n", (PinRef("A", "p"), PinRef("B", "p"), PinRef("C", "p"))),)


def test_a_met_trunk_with_one_tap_and_no_tree_is_handed_to_the_reference_loop_not_kept() -> None:
    """CASE2-CND-B: a one-tap trunk that still meets was kept with no finding; its tap is now one Refused."""
    env, grid, drawn = _trunk_of_three(wall=True)
    drawn = replace(drawn, wires=(drawn.wires[0], drawn.wires[2]))
    out = guard(env, grid, drawn)
    assert out.wires == ()
    assert out.lost == (Refused("n", (PinRef("B", "p"),)),)
