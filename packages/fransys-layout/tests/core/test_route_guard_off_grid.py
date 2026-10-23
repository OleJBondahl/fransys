"""XF-ROUTE (layout-0393): the guard reroutes a fixed wire whose pins stand off the wiring grid.

A box above a lamp, both at x = 604 (4 off the 8 grid): the box's top pin is wired to the lamp's
bottom pin by a straight wire through both bodies and the other net's pins. The guard must send it
round, leaving each pin along its footprint's normal and stepping to the grid, as a link does.
"""

from __future__ import annotations

from dataclasses import replace

from fransys_layout.core import Box
from fransys_layout.core.occupancy import Occupancy
from fransys_layout.core.outputs import PinXY, Placed, Wire
from fransys_layout.core.route_env import Drawn
from fransys_layout.core.route_guard import _reach, guard

from .route_fixtures import link_env

X = 604


def _env_and_grid():
    env = link_env({}, {})
    box_fp, lamp_fp = Box(588, 96, 116, 32), Box(590, 134, 74, 36)
    placed = {
        "B": Placed("B", 1, X, 112, "R0", box_fp, box_fp, (PinXY("1", X, 96), PinXY("2", X, 128))),
        "P": Placed(
            "P", 1, X, 152, "R180", lamp_fp, lamp_fp, (PinXY("in", X, 168), PinXY("out", X, 136))
        ),
    }
    env = replace(env, placed=placed)
    grid = Occupancy(100, 40, 8)
    for p in placed.values():
        grid.mark_box(p.footprint)
    return env, grid, (box_fp, lamp_fp)


def _guarded() -> tuple[Drawn, tuple[Box, Box]]:
    env, grid, boxes = _env_and_grid()
    through = Wire("long", 1, ((X, 96), (X, 168)), "straight")
    short = Wire("short", 1, ((X, 128), (X, 136)), "straight")
    return guard(env, grid, Drawn(wires=(short, through))), boxes


def test_a_wire_through_a_cell_between_off_grid_pins_is_rerouted() -> None:
    drawn, _ = _guarded()
    long = next(w for w in drawn.wires if w.net == "long")
    assert long.kind == "routed"
    assert long.points[0] == (X, 96)
    assert long.points[-1] == (X, 168)
    assert not drawn.findings


def test_the_rerouted_wire_keeps_out_of_both_bodies() -> None:
    drawn, boxes = _guarded()
    long = next(w for w in drawn.wires if w.net == "long")
    assert len(long.points) > 2, "a wire with no bend went through the cells"
    for (x0, y0), (x1, y1) in list(zip(long.points, long.points[1:], strict=False))[1:-1]:
        for b in boxes:
            lo_x, hi_x = sorted((x0, x1))
            lo_y, hi_y = sorted((y0, y1))
            inside = lo_x < b.x + b.w and hi_x > b.x and lo_y < b.y + b.h and hi_y > b.y
            assert not inside, ((x0, y0), (x1, y1), b)


def test_an_anchored_end_is_refused_on_a_blocked_port_end_and_accepted_off_it() -> None:
    env, _, _ = _env_and_grid()
    end, toward = (X, 96), (X, 168)
    out = _reach(env, end, toward)
    assert out is not None, "the unblocked off-grid end must reach the grid"
    blocked = replace(env, blocked_ends={"other": (out[-1],)})
    assert _reach(blocked, end, toward) is None
    elsewhere = replace(env, blocked_ends={"other": ((out[-1][0] + 80, out[-1][1]),)})
    assert _reach(elsewhere, end, toward) == out
