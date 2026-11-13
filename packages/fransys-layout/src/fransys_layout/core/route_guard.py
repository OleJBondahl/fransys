"""Stage 6 guard (R391, R419): a fixed wire meeting another net is rerouted by A*, else warned; a met trunk is rerouted as one tree (KI-731)."""

from __future__ import annotations

from dataclasses import replace
from itertools import pairwise
from typing import TYPE_CHECKING, NamedTuple

from .clearance import clear
from .errors import CoreError
from .flow_values import CrossLink
from .net_keys import net_of_key
from .outputs import Refused
from .route_astar import Leg, anchor, astar, simplify, tidy
from .route_env import hard_keeps, own_syms, pin_point, pin_side
from .route_tree import tree
from .values import Box, Finding, PinRef

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .clearance import Keep
    from .occupancy import Occupancy
    from .outputs import Wire
    from .route_env import Drawn, Rise, RouteEnv
    from .values import XY


def _in_hard(env: RouteEnv, wire: Wire, net: str, keeps: Sequence[Keep]) -> tuple[Keep, ...]:
    """The hard keeps a run of the wire shares interior area with, its own symbols' excepted."""
    own = own_syms(env, net, wire.net)
    return tuple(
        k
        for (ax, ay), (bx, by) in pairwise(wire.points)
        for k in clear(Box(min(ax, bx), min(ay, by), abs(bx - ax), abs(by - ay)), keeps, {}, edge="open", own=own)
    )


def _snap(end: XY, toward: XY, step: int) -> XY:
    """The wiring-grid point nearest `end` on its straight run toward `toward`."""
    (x, y), (tx, ty) = end, toward
    if x == tx and y != ty:
        return x, y + (-y % step if ty > y else -(y % step))
    return x + (-x % step if tx > x else -(x % step)), y


def _inside(box: Box, end: XY) -> bool:
    """Whether `end` is in the interior of `box`."""
    return box.x < end[0] < box.x + box.w and box.y < end[1] < box.y + box.h


def _reach(env: RouteEnv, end: XY, toward: XY) -> tuple[XY, ...] | None:
    """From a wire's end to a wiring-grid point: along its own run, else out of its footprint."""
    step = env.options.wiring_grid
    snapped = _snap(end, toward, step)
    if not (snapped[0] % step or snapped[1] % step):
        return (end, snapped)
    hit = next(((p, q.pin) for p in env.placed.values() for q in p.pin_xy if (q.x, q.y) == end), None)
    if hit is None:
        body = next((p for p in env.placed.values() if _inside(p.footprint, end)), None)
        if body is not None:
            msg = f"a wire end at {end} is inside the body of {body.sym} at none of its pins; end it at a pin or outside its footprint"
            raise CoreError(msg)
        return None
    out = anchor(end, hit[0].footprint, step, pin_side(env, hit[0].sym, hit[1]))
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
    hard: tuple[Keep, ...],
) -> bool:
    """Whether a wire meets a foreign net or a hard keep, a lane of the same fan included (KI-919).

    A fixed wire is never rerouted for a marker or hanging keep (R535 R-B): el still counts it.
    """
    hits = _in_hard(env, wire, net, hard)
    if wire.kind != "routed":
        hits = tuple(k for k in hits if k.kind == "body")
    return bool(grid.conflicts(net, wire.points)) or bool(hits)


def _settle(
    env: RouteEnv,
    grid: Occupancy,
    wire: Wire,
    hard: tuple[Keep, ...],
) -> tuple[Wire, bool]:
    """A marked two-end wire that meets is unmarked and rerouted, marked anew; True if it has no way."""
    net = net_of_key(wire.net)
    if not _meets(env, grid, wire, net, hard):
        return wire, False
    grid.unmark_wire(net, wire.points)
    points = _again(env, grid, wire, net)
    routed = wire if points is None else replace(wire, points=points, kind="routed")
    grid.mark_wire(net, routed.points)
    return routed, points is None


def _on_line(trunk: Wire, p: XY) -> bool:
    (x0, y), (x1, _) = trunk.points[0], trunk.points[-1]
    return p[1] == y and min(x0, x1) <= p[0] <= max(x0, x1)


class _Tree(NamedTuple):
    """What a trunk becomes: its wires, the reference it hands the loop, and the taps and rises it took over."""

    wires: tuple[Wire, ...]
    lost: tuple[Refused, ...] = ()
    taps: tuple[int, ...] = ()
    rises: tuple[Rise, ...] = ()


def _pin_at(env: RouteEnv, p: XY, key: str) -> PinRef | None:
    """The pin of the net `key` standing at `p`; a foreign pin there is no end of this net (KI-947)."""
    return next((r for r in env.net_pins.get(net_of_key(key), ()) if pin_point(env, r.sym, r.pin) == p), None)


def _taps(drawn: Drawn, trunk: Wire) -> tuple[tuple[int, ...], tuple[Rise, ...]]:
    """The drops and risers that end on the trunk's line, by index, and the rises aimed at it."""
    taps = tuple(j for j, w in enumerate(drawn.wires) if w.net == trunk.net and w.kind in ("drop", "riser") and _on_line(trunk, w.points[-1]))
    return taps, tuple(r for r in drawn.rises if r.net == trunk.net and _on_line(trunk, r.target))


def _retree(env: RouteEnv, grid: Occupancy, drawn: Drawn, i: int) -> tuple[Wire, ...] | None:
    """A trunk rerouted as one tree over the points of all its taps; None, trunk marked as placed, when there is none.

    The drops stay as drawn. The first-to-last reroute dropped every inner tap (KI-731).
    """
    trunk, net = drawn.wires[i], net_of_key(drawn.wires[i].net)
    taps, aimed = _taps(drawn, trunk)
    first, last = trunk.points[0], trunk.points[-1]
    inner = dict.fromkeys(p for p in (*(drawn.wires[j].points[-1] for j in taps), *(r.target for r in aimed)) if p not in (first, last))
    grid.unmark_wire(net, trunk.points)
    reached = [_reach(env, first, last), _reach(env, last, first), *(_reach(env, p, last) for p in inner)]
    anchors = [a for a in reached if a is not None]
    found = tree(env, grid, CrossLink(net, ()), anchors) if len(anchors) == len(reached) else None
    if found is None:
        grid.mark_wire(net, trunk.points)
        return None
    return tuple(replace(w, net=trunk.net) for w in found)


def _hand(env: RouteEnv, drawn: Drawn, i: int) -> _Tree | None:
    """A wire still meeting with no way keeps no wire: the pins of its ends and taps are one Refused for the reference loop.

    None when it has no pin: the wire is then warned, never kept silently.
    """
    wire = drawn.wires[i]
    taps, aimed = _taps(drawn, wire)
    at = (wire.points[0], wire.points[-1], *(drawn.wires[j].points[0] for j in taps))
    pins = tuple(q for q in (*(_pin_at(env, p, wire.net) for p in at), *(r.pin for r in aimed)) if q is not None)
    return _Tree((), (Refused(net_of_key(wire.net), pins),), taps, aimed) if pins else None


def _settled(env: RouteEnv, grid: Occupancy, drawn: Drawn, hard: tuple[Keep, ...]) -> tuple[dict[int, tuple[Wire, ...]], list[int]]:
    """Every wire marked, then trunks first (R439) and the rest: what each becomes, and the ones with no way."""
    wires, stuck = drawn.wires, list[int]()
    kept: dict[int, tuple[Wire, ...]] = {}
    for w in wires:
        grid.mark_wire(net_of_key(w.net), w.points)
    for i in [i for i, w in enumerate(wires) if w.kind == "trunk"] + [i for i, w in enumerate(wires) if w.kind != "trunk"]:
        if not _meets(env, grid, wires[i], net_of_key(wires[i].net), hard):
            kept[i] = (wires[i],)
        elif wires[i].kind == "trunk":
            found = _retree(env, grid, drawn, i)
            kept[i] = found or (wires[i],)
            stuck += [i] * (found is None)
        else:
            w, no_way = _settle(env, grid, wires[i], hard)
            kept[i] = (w,)
            stuck += [i] * no_way
    return kept, stuck


def guard(env: RouteEnv, grid: Occupancy, drawn: Drawn) -> Drawn:
    """Every fixed wire is marked first (R535 R-D); trunks first (R439), a meeting one is rerouted.

    A trunk is rerouted as one tree over its taps (KI-731). A wire with no way is kept while the others settle; one that
    still meets then is warned, or its pins go to the reference loop.
    """
    hard, wires = hard_keeps(env), drawn.wires
    kept, stuck = _settled(env, grid, drawn, hard)
    still = [i for i in stuck if _meets(env, grid, wires[i], net_of_key(wires[i].net), hard)]
    trunk_of = {j: i for i, w in enumerate(wires) if w.kind == "trunk" for j in _taps(drawn, w)[0]}
    handed = {i: t for i in dict.fromkeys(trunk_of.get(s, s) for s in still) if (t := _hand(env, drawn, i))}
    gone = {j for t in handed.values() for j in t.taps}
    warned = tuple(_warn(env, wires[i], net_of_key(wires[i].net)) for i in still if trunk_of.get(i, i) not in handed)
    return replace(
        drawn,
        wires=tuple(w for i in range(len(wires)) if i not in gone for w in (handed[i].wires if i in handed else kept[i])),
        findings=drawn.findings + warned,
        rises=tuple(r for r in drawn.rises if not any(r in t.rises for t in handed.values())),
        lost=drawn.lost + tuple(r for t in handed.values() for r in t.lost),
    )
