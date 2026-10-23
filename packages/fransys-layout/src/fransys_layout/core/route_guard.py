"""Stage 6 guard (R391, R419): a fixed wire meeting another net is rerouted by A*, else warned."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from .route_astar import Leg, astar, simplify, tidy
from .values import Finding

if TYPE_CHECKING:
    from .occupancy import Occupancy
    from .outputs import Wire
    from .route_env import Drawn, RouteEnv
    from .values import XY


def _net(wire: Wire) -> str:
    """A bundle trunk `f:N` carries net N: its stems end on it by the bundle convention."""
    return wire.net.removeprefix("f:")


def _snap(end: XY, toward: XY, step: int) -> XY:
    """The wiring-grid point nearest `end` on its straight run toward `toward`."""
    (x, y), (tx, ty) = end, toward
    if x == tx and y != ty:
        return x, y + (-y % step if ty > y else -(y % step))
    if y == ty and x != tx:
        return x + (-x % step if tx > x else -(x % step)), y
    return end


def _again(env: RouteEnv, grid: Occupancy, wire: Wire, net: str) -> tuple[XY, ...] | None:
    """The wire's ends joined by A*; an off-grid end keeps a short stub along its own run."""
    step = env.options.wiring_grid
    first, last = wire.points[0], wire.points[-1]
    a = _snap(first, wire.points[1], step)
    b = _snap(last, wire.points[-2], step)
    if any(x % step or y % step for x, y in (a, b)):
        return None
    start, goal = ((x // step, y // step) for x, y in (a, b))
    leg = Leg(net, start, goal, frozenset((start, goal)))
    path = astar(grid, leg, env.options)
    if path is None:
        return None
    mid = tidy(simplify(path, step))
    return tidy(tuple(p for p in (first, *mid, last)))


def _warn(env: RouteEnv, wire: Wire, net: str) -> Finding:
    text = (
        f"net {net} on page {env.page} has a {wire.kind} wire from {wire.points[0]} to "
        f"{wire.points[-1]} that meets another net and has no free path, so it stays as "
        "placed: move a symbol or widen the gap beside it"
    )
    return Finding("WIRE_MEETS_NET", text, env.page, net)


def guard(env: RouteEnv, grid: Occupancy, drawn: Drawn) -> Drawn:
    """Fixed wires, trunks first (R439): one meeting a foreign net is rerouted, else warned."""
    kept: dict[int, Wire] = {}
    warned = []
    bundled = frozenset(
        n for f in env.fans.values() if f.lanes > 1 for n in (f.id.removeprefix("f:"), *f.nets)
    )
    wires = drawn.wires
    first = [i for i, w in enumerate(wires) if w.kind == "trunk"]
    for i in (*first, *(i for i, w in enumerate(wires) if w.kind != "trunk")):
        fixed = wires[i]
        net, wire = _net(fixed), fixed
        if grid.touches(net, fixed.points, bundled if net in bundled else frozenset()):
            points = _again(env, grid, fixed, net)
            if points is None:
                warned.append(_warn(env, fixed, net))
            else:
                wire = replace(fixed, points=points, kind="routed")
        grid.mark_wire(net, wire.points)
        kept[i] = wire
    return replace(
        drawn,
        wires=tuple(kept[i] for i in range(len(wires))),
        findings=drawn.findings + tuple(warned),
    )
