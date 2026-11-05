"""R535 R-D (layout-0395): every fixed wire is marked on the guard grid before any is rerouted.

Wire A crosses a footprint, so it is rerouted; wire C of another net stands later in the loop on a
cell of A's free reroute. A reroute that cannot see C takes the cells, and C is then moved.
"""

from __future__ import annotations

from fransys_layout.core.occupancy import Occupancy
from fransys_layout.core.outputs import Wire
from fransys_layout.core.route_env import Drawn
from fransys_layout.core.route_guard import guard

from .test_route_guard_hard import ACROSS
from .test_route_guard_off_grid import _env_and_grid


def _on_a_run(alone: Wire) -> Wire:
    """A horizontal wire of net c on the longest horizontal run of A's reroute."""
    runs = [(a, b) for a, b in zip(alone.points, alone.points[1:], strict=False) if a[1] == b[1]]
    (x0, y), (x1, _) = max(runs, key=lambda r: abs(r[1][0] - r[0][0]))
    lo, hi = sorted((x0, x1))
    return Wire("c", 1, ((lo + 8, y), (hi - 8, y)), "straight")


def _run() -> tuple[Wire, Wire, Occupancy]:
    env, grid, _ = _env_and_grid()
    alone = guard(env, grid, Drawn(wires=(ACROSS,))).wires[0]
    assert alone.kind == "routed"
    standing = _on_a_run(alone)
    env, grid, _ = _env_and_grid()
    a, c = guard(env, grid, Drawn(wires=(ACROSS, standing))).wires
    return a, c, grid


def test_a_later_fixed_wire_is_not_taken_by_an_earlier_reroute() -> None:
    a, c, grid = _run()
    assert c.kind == "straight", "the standing wire was moved by A's reroute"
    assert a.points[0] == (496, 112)
    assert a.points[-1] == (776, 112)
    assert not grid.conflicts("c", c.points)
    assert not grid.conflicts("n", a.points)


def test_the_old_marks_of_a_rerouted_wire_are_gone() -> None:
    a, c, grid = _run()
    fresh = Occupancy(grid.cols, grid.rows, grid.step)
    for p in (a, c):
        fresh.mark_wire(p.net, p.points)
    assert grid.used == fresh.used
    assert grid.ends == fresh.ends
    assert {k: v for k, v in grid.runs.items() if v} == {k: v for k, v in fresh.runs.items() if v}
