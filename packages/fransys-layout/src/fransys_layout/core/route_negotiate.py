"""Stage 6 negotiation (SPEC-022 C7, R606, R623): rises and links meet at a price.

Each soft round routes every item again with R391 priced, not refused; a cell where items meet
costs more every round. The check fails the costliest item that still breaks R391; the repair
tail then routes each failed item alone on the settled map, hard, with the same A* (R623).
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise
from typing import TYPE_CHECKING

from .flow_values import CrossLink
from .occupancy import cells_between
from .route_tree import mark_anchors, rise_wire, tree

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .occupancy import Occupancy
    from .outputs import Wire
    from .route_env import Rise, RouteEnv
    from .values import XY

Routed = list["tuple[Wire, ...] | None"]


@dataclass(frozen=True, slots=True)
class Negotiated:
    """What was drawn and what was not.

    `routed` holds each routed link's wires by net, in order; `risen` the wires of the routed
    rises; `failed` the links and `lost` the rises that no legal route was found for.
    """

    routed: dict[str, tuple[Wire, ...]]
    risen: tuple[Wire, ...]
    failed: tuple[str, ...]
    lost: tuple[Rise, ...]


def _conflicts(grid: Occupancy, net: str, wires: Sequence[Wire]) -> list[tuple[XY, str]]:
    """Where the wires meet another net against R391."""
    return [c for w in wires for c in grid.conflicts(net, w.points)]


def _crossed(grid: Occupancy, net: str, wires: Sequence[Wire]) -> list[tuple[XY, str]]:
    """Where the wires cross another net's wire, as (cell, axis): priced, not refused (R647)."""
    return [
        (cell, axis)
        for w in wires
        for p, q in pairwise(w.points)
        for axis in ("h" if p[1] == q[1] else "v",)
        for cell in cells_between(p, q, grid.step)
        if grid.crossing(cell, axis, net)
    ]


def _lay(env: RouteEnv, grid: Occupancy, item: CrossLink | Rise) -> tuple[Wire, ...] | None:
    """The item's wires by A*, marked on the map; None on a dead end, partial marks left."""
    if not isinstance(item, CrossLink):
        wire = rise_wire(env, grid, item)
        return None if wire is None else (wire,)
    mark_anchors(env, grid, item)
    return tree(env, grid, item)


def _lift(grid: Occupancy, item: CrossLink | Rise, wires: Sequence[Wire]) -> None:
    """Take the item off the map: a link's whole net, a rise its own wire (the trunk stays)."""
    if isinstance(item, CrossLink):
        grid.remove_net(item.net)
        return
    for w in wires:
        grid.unmark_wire(w.net, w.points)


def _round(env: RouteEnv, grid: Occupancy, items: Sequence[CrossLink | Rise], routed: Routed) -> None:
    """Every item, in order, rips up and routes again; a dead end leaves nothing."""
    for k, item in enumerate(items):
        _lift(grid, item, routed[k] or ())
        routed[k] = _lay(env, grid, item)
        if routed[k] is None:
            _lift(grid, item, ())


def _heat(grid: Occupancy, items: Sequence[CrossLink | Rise], routed: Routed, amount: int) -> bool:
    """Each cell where an item meets another against R391 costs `amount` more from now on; True when any did."""
    heated = False
    for k, item in enumerate(items):
        for cell, axis in _conflicts(grid, item.net, routed[k] or ()):
            grid.add_history(cell, axis, amount)
            heated = True
    return heated


def _history(grid: Occupancy, wires: Sequence[Wire]) -> int:
    """The history over every cell and axis the wires run on."""
    return sum(
        grid.history.get((cell, "h" if p[1] == q[1] else "v"), 0)
        for w in wires
        for p, q in pairwise(w.points)
        for cell in cells_between(p, q, grid.step)
    )


def _costliest(grid: Occupancy, meeting: Sequence[int], routed: Routed) -> int:
    """The index whose cells hold the most history; a tie goes to the last in order."""
    best, most = meeting[0], -1
    for k in meeting:
        held = _history(grid, routed[k] or ())
        if held >= most:
            best, most = k, held
    return best


def _check(grid: Occupancy, items: Sequence[CrossLink | Rise], routed: Routed) -> list[int]:
    """The costliest item that still breaks R391 leaves the map, until none does; their indices."""
    out: list[int] = []
    while meeting := [k for k, it in enumerate(items) if _conflicts(grid, it.net, routed[k] or ())]:
        k = _costliest(grid, meeting, routed)
        _lift(grid, items[k], routed[k] or ())
        routed[k] = None
        out.append(k)
    return out


def _repair(
    env: RouteEnv,
    grid: Occupancy,
    items: Sequence[CrossLink | Rise],
    failed: Sequence[int],
    routed: Routed,
) -> None:
    """Each failed item alone on the settled map, hard, costliest first (R623, R596)."""
    for link in (items[k] for k in failed):
        if isinstance(link, CrossLink):
            mark_anchors(env, grid, link)
    for k in failed:
        routed[k] = _lay(env, grid, items[k])
        if routed[k] is None:
            _lift(grid, items[k], ())


def _relay(env: RouteEnv, grid: Occupancy, item: CrossLink | Rise, old: tuple[Wire, ...]) -> tuple[Wire, ...]:
    """The item alone again on the settled map, hard; kept only when it crosses less, else the old wires return."""
    before = len(_crossed(grid, item.net, old))
    _lift(grid, item, old)
    new = _lay(env, grid, item)
    if new is not None and len(_crossed(grid, item.net, new)) < before:
        return new
    _lift(grid, item, ())
    if isinstance(item, CrossLink):
        mark_anchors(env, grid, item)
    for w in old:
        grid.mark_wire(w.net, w.points)
    return old


def _ripup(env: RouteEnv, grid: Occupancy, items: Sequence[CrossLink | Rise], routed: Routed) -> None:
    """Each round lays the `ripup_worst` most-crossing routed links alone again (R596); it stops when none crosses."""
    for _ in range(env.options.reroute_rounds):
        crossing = [(len(_crossed(grid, items[k].net, w)), k) for k, w in enumerate(routed) if w and isinstance(items[k], CrossLink)]
        top = [k for n, k in sorted(crossing, key=lambda c: -c[0])[: env.options.ripup_worst] if n]
        if not top:
            return
        for k in top:
            routed[k] = _relay(env, grid, items[k], routed[k] or ())


def negotiate(env: RouteEnv, grid: Occupancy, links: Sequence[CrossLink], rises: Sequence[Rise] = ()) -> Negotiated:
    """Route rises and links at `share_penalty` until history parts them; repair the rest; relay the worst crossers."""
    options, items = env.options, (*rises, *links)
    routed: Routed = [None] * len(items)
    grid.share_cost = options.share_penalty
    for _ in range(1 + options.reroute_rounds):
        _round(env, grid, items, routed)
        if not _heat(grid, items, routed, options.history_step):
            break
    grid.share_cost = 0
    dead = [k for k, w in enumerate(routed) if w is None]
    _repair(env, grid, items, [*_check(grid, items, routed), *dead], routed)
    _ripup(env, grid, items, routed)
    n = len(rises)
    return Negotiated(
        {ln.net: w for ln, w in zip(links, routed[n:], strict=True) if w is not None},
        tuple(w for ws in routed[:n] for w in ws or ()),
        tuple(ln.net for ln, w in zip(links, routed[n:], strict=True) if w is None),
        tuple(r for r, w in zip(rises, routed[:n], strict=True) if w is None),
    )
