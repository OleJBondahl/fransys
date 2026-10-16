"""Stage 6 trees: one net's ends joined by A*, the first pair, then each end to the net's tree."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from .keys import natural_key
from .outputs import Wire
from .route_astar import Leg, anchor, astar, simplify, tidy
from .route_env import pin_point

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .occupancy import Occupancy
    from .route_env import Rise, RouteEnv
    from .values import XY, CrossLink, Options

MIN_ENDS = 2  # a net with fewer placed ends has nothing to join
Window = tuple[int, int, int, int]
WINDOW = 3  # tracks the search may stray from the link's bounding box before the whole page


def end_anchors(env: RouteEnv, link: CrossLink) -> list[tuple[XY, ...]]:
    """Each end's anchor: its pin, then the grid point outside its footprint where A* starts.

    The first two ends keep the link's order; every further end follows in `natural_key` order.
    """
    step = env.options.wiring_grid
    found = [
        (a, pin) for a in link.ends if (pin := pin_point(env, a.pin.sym, a.pin.pin)) is not None
    ]
    rest = sorted(found[2:], key=lambda e: natural_key(f"{e[0].pin.sym}.{e[0].pin.pin}"))
    return [anchor(pin, env.placed[a.pin.sym].footprint, step) for a, pin in [*found[:2], *rest]]


def _cell(p: XY, step: int) -> XY:
    return (p[0] // step, p[1] // step)


def _window(anchors: Sequence[tuple[XY, ...]], step: int) -> Window:
    cells = [_cell(a[-1], step) for a in anchors]
    xs, ys = [c[0] for c in cells], [c[1] for c in cells]
    return (min(xs) - WINDOW, min(ys) - WINDOW, max(xs) + WINDOW, max(ys) + WINDOW)


def search(grid: Occupancy, leg: Leg, window: Window, options: Options) -> tuple[XY, ...] | None:
    """A* inside the link's window; a failure there is retried on the whole page."""
    path = astar(grid, replace(leg, window=window), options)
    return path if path is not None else astar(grid, leg, options)


def _further(
    env: RouteEnv,
    grid: Occupancy,
    net: str,
    ctx: tuple[Sequence[tuple[XY, ...]], Sequence[XY], Window],
) -> tuple[Wire, ...] | None:
    """The ends past the second, each by A* to the cells the pair holds; None on a dead end."""
    ends, first, window = ctx
    step, held = env.options.wiring_grid, set(first)
    out: list[Wire] = []
    for end in ends:
        start = _cell(end[-1], step)
        leg = Leg(net, start, min(held), frozenset((start,)), frozenset(held))
        path = search(grid, leg, window, env.options)
        if path is None:
            return None
        pts = simplify(path, step)
        grid.mark_wire(net, pts)
        held.update(path)
        out.append(Wire(net, env.page, tidy([*end, *pts]), "routed"))
    return tuple(out)


def tree(env: RouteEnv, grid: Occupancy, link: CrossLink) -> tuple[Wire, ...] | None:
    """The net's ends as wires: the first to the second, each further end to the cells held.

    The held cells are free for the own net. None on a dead end; the caller clears the net.
    """
    step, net = env.options.wiring_grid, link.net
    anchors = end_anchors(env, link)
    if len(anchors) < MIN_ENDS:
        return ()
    window = _window(anchors, step)
    start, goal = _cell(anchors[0][-1], step), _cell(anchors[1][-1], step)
    path = search(grid, Leg(net, start, goal, frozenset((start, goal))), window, env.options)
    if path is None:
        return None
    pts = simplify(path, step)
    grid.mark_wire(net, pts)
    ends = tidy([*anchors[0][:-1], *pts, *reversed(anchors[1][:-1])])
    more = _further(env, grid, net, (anchors[2:], path, window))
    return None if more is None else (Wire(net, env.page, ends, "routed"), *more)


def rise_wire(env: RouteEnv, grid: Occupancy, r: Rise) -> Wire | None:
    """A rise to its trunk cell; None when it finds no path or its target is off the grid."""
    step = env.options.wiring_grid
    pin = anchor(r.start, env.placed[r.sym].footprint, step)
    start, goal = _cell(pin[-1], step), _cell(r.target, step)
    path = None
    if r.target[0] % step == 0 and r.target[1] % step == 0:
        path = astar(grid, Leg(r.net, start, goal, frozenset((start, goal))), env.options)
    if path is None:
        return None
    pts = simplify(path, step)
    grid.mark_wire(r.net, pts)
    return Wire(r.net, env.page, tidy([*pin, *pts]), r.drawn_as)
