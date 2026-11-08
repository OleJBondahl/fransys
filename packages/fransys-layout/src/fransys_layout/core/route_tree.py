"""Stage 6 trees: one net's ends joined by A*, the first pair, then each end to the net's tree."""

from __future__ import annotations

from itertools import pairwise
from typing import TYPE_CHECKING

from .keys import natural_key
from .outputs import Wire
from .route_astar import Leg, anchor, astar, simplify, tidy
from .route_env import own_syms, pin_point, pin_side

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence

    from .flow_values import CrossLink
    from .occupancy import Occupancy
    from .route_env import Rise, RouteEnv
    from .values import XY

MIN_ENDS = 2  # a net with fewer placed ends has nothing to join


def end_anchors(env: RouteEnv, link: CrossLink) -> list[tuple[XY, ...]]:
    """Each end's anchor: its pin, then the grid point outside its footprint where A* starts.

    The first two ends keep the link's order; every further end follows in `natural_key` order.
    """
    step = env.options.wiring_grid
    found = [(a, pin) for a in link.ends if (pin := pin_point(env, a.pin.sym, a.pin.pin)) is not None]
    rest = sorted(found[2:], key=lambda e: natural_key(f"{e[0].pin.sym}.{e[0].pin.pin}"))
    return [anchor(pin, env.placed[a.pin.sym].footprint, step, pin_side(env, a.pin.sym, a.pin.pin)) for a, pin in [*found[:2], *rest]]


def mark_anchors(env: RouteEnv, grid: Occupancy, link: CrossLink) -> None:
    """The link's anchor runs on the map, so another net's wire keeps off its ends (R391)."""
    for anchors in end_anchors(env, link):
        grid.mark_wire(link.net, anchors)


def _cell(p: XY, step: int) -> XY:
    return (p[0] // step, p[1] // step)


def _held(path: Sequence[XY], wire: Sequence[XY], step: int) -> set[XY]:
    """The path's cells that the tidied wire still passes; tidy drops a backtrack corner at an end."""
    segs = list(pairwise(wire))
    return {
        c
        for c in path
        if any(min(a[0], b[0]) <= c[0] * step <= max(a[0], b[0]) and min(a[1], b[1]) <= c[1] * step <= max(a[1], b[1]) for a, b in segs)
    }


def _further(
    env: RouteEnv,
    grid: Occupancy,
    net: str,
    ctx: tuple[Sequence[tuple[XY, ...]], Collection[XY]],
) -> tuple[Wire, ...] | None:
    """The ends past the second, each by A* to the cells the pair holds; None on a dead end."""
    ends, first = ctx
    step, held = env.options.wiring_grid, set(first)
    out: list[Wire] = []
    for end in ends:
        start = _cell(end[-1], step)
        own = own_syms(env, net, net)
        leg = Leg(net, start, min(held), frozenset((start,)), frozenset(held), own)
        path = astar(grid, leg, env.options)
        if path is None:
            return None
        pts = simplify(path, step)
        grid.mark_wire(net, pts)
        wire = tidy([*end, *pts])
        held.update(_held(path, wire, step))
        out.append(Wire(net, env.page, wire, "routed"))
    return tuple(out)


def tree(env: RouteEnv, grid: Occupancy, link: CrossLink, anchors: Sequence[tuple[XY, ...]] | None = None) -> tuple[Wire, ...] | None:
    """The net's ends as wires: the first to the second, each further end to the cells held.

    The ends are the anchors of the link's pins, or the `anchors` given (the guard's trunk taps).
    The held cells are free for the own net. None on a dead end; the caller clears the net.
    """
    step, net = env.options.wiring_grid, link.net
    anchors = end_anchors(env, link) if anchors is None else anchors
    if len(anchors) < MIN_ENDS:
        return ()
    start, goal = _cell(anchors[0][-1], step), _cell(anchors[1][-1], step)
    leg = Leg(net, start, goal, frozenset((start, goal)), own=own_syms(env, net, net))
    path = astar(grid, leg, env.options)
    if path is None:
        return None
    pts = simplify(path, step)
    grid.mark_wire(net, pts)
    ends = tidy([*anchors[0][:-1], *pts, *reversed(anchors[1][:-1])])
    more = _further(env, grid, net, (anchors[2:], _held(path, ends, step)))
    return None if more is None else (Wire(net, env.page, ends, "routed"), *more)


def rise_wire(env: RouteEnv, grid: Occupancy, r: Rise) -> Wire | None:
    """A rise to its trunk cell, the grid point nearest its target, then along the line to it; None when A* finds no path."""
    step = env.options.wiring_grid
    pin = anchor(r.start, env.placed[r.pin.sym].footprint, step, pin_side(env, r.pin.sym, r.pin.pin))
    start, goal = _cell(pin[-1], step), _cell((r.target[0] + step // 2, r.target[1] + step // 2), step)
    leg = Leg(r.net, start, goal, frozenset((start, goal)), own=own_syms(env, r.net, r.net))
    path = astar(grid, leg, env.options)
    if path is None:
        return None
    pts = simplify(path, step)
    grid.mark_wire(r.net, pts)
    return Wire(r.net, env.page, tidy([*pin, *pts, r.target]), r.drawn_as)
