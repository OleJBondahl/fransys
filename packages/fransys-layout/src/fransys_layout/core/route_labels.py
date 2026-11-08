"""Stage 6b: a page's labels, stood after its fixed wires and before its A* round (TAG-CORNERS, layout-0515).

A label that is blocked at every candidate hands its first rung to its owner's footprint as a demand (R1831):
widen cuts again; still blocked after that, ANNEX_UNPLACED names it.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from .annex import place_labels, text_keeps
from .errors import CoreError
from .geometry import union
from .outputs import Demand
from .route_runs import named
from .values import Box

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from .annex_values import Annex, AnnexBox
    from .clearance import Keep
    from .outputs import Wire
    from .route_env import RouteEnv
    from .sym_values import Turned
    from .values import Finding, PlacementProblem


def _need(env: RouteEnv, annex: Annex) -> Demand | None:
    """The tracks the gap beside the owner's column must hold for the box: the label's width, widening the pitch (T6)."""
    col = next((c for c in env.columns if any(cell.sym == annex.owner for lane in c.lanes for cell in lane.cells)), None)
    if col is None:
        return None
    gap = next((g for g in env.gaps if g.left == col.id), None) or next((g for g in env.gaps if g.right == col.id), None)
    if gap is None:
        return None
    more = -(-(annex.size.w + env.options.label_gap) // env.options.wiring_grid)
    return Demand(gap.id, max(gap.tracks, 1) + more)


def _grown(g: Box | None, rooms: Mapping[str, int], box: Box | None) -> Box | None:
    for side in rooms:
        if side not in ("N", "S"):
            msg = f"a room demand on side {side!r}: only N and S rooms grow a footprint"
            raise CoreError(msg)
    g = g and (union(g, box) if box else g)
    north, south = rooms.get("N", 0), rooms.get("S", 0)
    return g and Box(g.x, g.y - north, g.w, g.h + north + south)


def _held(view: Turned, rooms: Mapping[str, int], box: Box | None) -> Turned:
    """The view whose footprints also hold `box` (relative to the origin) and each side's room in G (R1831, R1961)."""
    return replace(view, footprint=_grown(view.footprint, rooms, box), row_footprint=_grown(view.row_footprint, rooms, box))


def roomed(problem: PlacementProblem, needs: Iterable[Demand]) -> PlacementProblem:
    """`problem` whose owners of the room and rung demands hold that box and room: a footprint is a keep-out, so the solve clears it."""
    ask: dict[str, tuple[dict[str, int], Box | None]] = {}
    for d in needs:
        if d.owner and (d.room or d.box):
            rooms, box = ask.get(d.owner, ({}, None))
            rooms[d.side] = max(rooms.get(d.side, 0), d.room)
            ask[d.owner] = (rooms, d.box if box is None or d.box is None else union(box, d.box))
    if not ask:
        return problem
    fits = {s.id: {o: _held(v, *ask[s.id]) for o, v in s.views.items()} for s in problem.symbols if s.id in ask}
    return replace(problem, symbols=tuple(replace(s, views=fits[s.id]) if s.id in fits else s for s in problem.symbols))


def page_labels(env: RouteEnv, wires: Sequence[Wire]) -> tuple[tuple[AnnexBox, ...], tuple[Keep, ...], tuple[Finding, ...], tuple[Demand, ...]]:
    """The page's labels, the keeps of those that stand, ANNEX_UNPLACED for the others and their demands on the gaps."""
    if not env.annexes:
        return (), (), (), ()
    ink = ([*wires, *env.anchor_leads], [k.box for k in env.obstacles])
    placed = {**env.placed, **{k: p for k, (_, p) in env.runs.items()}}
    on = (env.page, env.area, env.options.label_gap, env.options.label_moves)
    labels, found, blocked = named(env.runs, *place_labels(env.annexes, placed, ink, on, env.labels))
    standing = text_keeps(a for i, a in enumerate(labels) if i not in blocked)
    gaps = (_need(env, replace(a, owner=env.runs[a.owner][1].sym) if a.owner in env.runs else a) for a in (env.annexes[i] for i in blocked))
    return tuple(labels), standing, tuple(found), (*blocked.values(), *(d for d in gaps if d))
