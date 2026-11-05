"""Stage 6 guard (R391, R419): a fixed wire meeting another net is rerouted by A*, else warned."""

from __future__ import annotations

from dataclasses import replace
from itertools import pairwise
from typing import TYPE_CHECKING

from .clearance import clear
from .net_keys import net_of_key
from .route_astar import Leg, anchor, astar, simplify, tidy
from .route_env import hard_keeps, own_syms
from .values import Box, Finding

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .clearance import Keep
    from .occupancy import Occupancy
    from .outputs import Wire
    from .route_env import Drawn, RouteEnv
    from .values import XY


def _in_hard(env: RouteEnv, wire: Wire, net: str, keeps: Sequence[Keep]) -> tuple[Keep, ...]:
    """The hard keeps a run of the wire shares interior area with, its own symbols' excepted."""
    own = own_syms(env, net, wire.net)
    return tuple(
        k
        for (ax, ay), (bx, by) in pairwise(wire.points)
        for k in clear(Box(min(ax, bx), min(ay, by), abs(bx - ax), abs(by - ay)), keeps, {}, gap=-1, own=own)
    )


def _snap(end: XY, toward: XY, step: int) -> XY:
    """The wiring-grid point nearest `end` on its straight run toward `toward`."""
    (x, y), (tx, ty) = end, toward
    if x == tx and y != ty:
        return x, y + (-y % step if ty > y else -(y % step))
    return x + (-x % step if tx > x else -(x % step)), y


def _reach(env: RouteEnv, end: XY, toward: XY) -> tuple[XY, ...] | None:
    """From a wire's end to a wiring-grid point: along its own run, else out of its footprint."""
    step = env.options.wiring_grid
    snapped = _snap(end, toward, step)
    if not (snapped[0] % step or snapped[1] % step):
        return (end, snapped)
    ex, ey = end
    box = next(
        (f for f in (p.footprint for p in env.placed.values()) if f.x <= ex <= f.x + f.w and f.y <= ey <= f.y + f.h),
        None,
    )
    if box is None:
        return None
    out = anchor(end, box, step)
    blocked = {(x // step, y // step) for pts in env.blocked_ends.values() for x, y in pts}
    return None if (out[-1][0] // step, out[-1][1] // step) in blocked else out  # R482, R472


def _again(env: RouteEnv, grid: Occupancy, wire: Wire, net: str) -> tuple[XY, ...] | None:
    """The ends joined by A*; an off-grid end leaves along its run or out of its footprint."""
    step = env.options.wiring_grid
    head = _reach(env, wire.points[0], wire.points[1])
    tail = _reach(env, wire.points[-1], wire.points[-2])
    if head is None or tail is None:
        return None
    start, goal = ((x // step, y // step) for x, y in (head[-1], tail[-1]))
    leg = Leg(net, start, goal, frozenset((start, goal)), own=own_syms(env, net, wire.net))
    path = astar(grid, leg, env.options)
    if path is None:
        return None
    back: list[XY] = []  # the tail chain read from the grid point to the pin
    for pt in tail[:-1]:
        back.insert(0, pt)
    return tidy((*head[:-1], *simplify(path, step), *back))


def _warn(env: RouteEnv, wire: Wire, net: str) -> Finding:
    text = (
        f"net {net} on page {env.page} has a {wire.kind} wire from {wire.points[0]} to "
        f"{wire.points[-1]} that meets another net and has no free path, so it stays as "
        "placed: move a symbol or widen the gap beside it"
    )
    return Finding("WIRE_MEETS_NET", text, env.page, net)


def _meets(
    env: RouteEnv,
    grid: Occupancy,
    wire: Wire,
    net: str,
    kept: tuple[frozenset[str], tuple[Keep, ...]],
) -> bool:
    """Whether a wire meets a foreign net or a hard keep (`kept` is bundled nets, keeps).

    A fixed wire is never rerouted for a marker or hanging keep (R535 R-B): el still counts it.
    """
    bundled, hard = kept
    skip = bundled if net in bundled else frozenset()
    hits = _in_hard(env, wire, net, hard)
    if wire.kind != "routed":
        hits = tuple(k for k in hits if k.kind == "body")
    return bool(grid.conflicts(net, wire.points, skip)) or bool(hits)


def _settle(
    env: RouteEnv,
    grid: Occupancy,
    wire: Wire,
    kept: tuple[frozenset[str], tuple[Keep, ...]],
) -> tuple[Wire, bool]:
    """A marked wire that meets is unmarked and rerouted, marked anew; True if it has no way."""
    net = net_of_key(wire.net)
    if not _meets(env, grid, wire, net, kept):
        return wire, False
    grid.unmark_wire(net, wire.points)
    points = _again(env, grid, wire, net)
    routed = wire if points is None else replace(wire, points=points, kind="routed")
    grid.mark_wire(net, routed.points)
    return routed, points is None


def guard(env: RouteEnv, grid: Occupancy, drawn: Drawn) -> Drawn:
    """Every fixed wire is marked first (R535 R-D); trunks first (R439), a meeting one is rerouted.

    A wire with no way is warned only if it still meets once every other wire has settled.
    """
    kept: dict[int, Wire] = {}
    stuck = []
    bundled = frozenset(n for f in env.fans.values() if f.lanes > 1 for n in (net_of_key(f.id), *f.nets))
    wires, hard = drawn.wires, hard_keeps(env)
    for w in wires:
        grid.mark_wire(net_of_key(w.net), w.points)
    first = [i for i, w in enumerate(wires) if w.kind == "trunk"]
    for i in (*first, *(i for i, w in enumerate(wires) if w.kind != "trunk")):
        kept[i], no_way = _settle(env, grid, wires[i], (bundled, hard))
        stuck += [i] * no_way
    warned = tuple(
        _warn(env, wires[i], net_of_key(wires[i].net)) for i in stuck if _meets(env, grid, wires[i], net_of_key(wires[i].net), (bundled, hard))
    )
    return replace(
        drawn,
        wires=tuple(kept[i] for i in range(len(wires))),
        findings=drawn.findings + warned,
    )
