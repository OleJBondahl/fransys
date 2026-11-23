"""Stage 7, widen: the bound of its pass loop (R1981) and the problem and demands each pass hands the next."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from .errors import CoreError
from .geometry import union
from .outputs import Demand

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from .outputs import Placement, Refused, Routes
    from .values import Options, PinRef, PlacementProblem


def settled(rounds: int, options: Options, asked: Iterable[Demand], *, quiet: bool) -> bool:
    """Whether pass `rounds` ended the loop: a quiet pass after the first; a busy one past `widen_rounds_limit` raises.

    Grants only grow, so a pass that still grants after the limit is a loop, never a hang.
    """
    if not quiet and rounds >= options.widen_rounds_limit:
        msg = f"widen granted again after {rounds} rounds; unmet room asks: {[(d.owner, d.side, d.room, d.box) for d in asked]}"
        raise CoreError(msg)
    return bool(rounds) and quiet


def unspent(tried: Mapping[str, int], routes: Routes, options: Options) -> tuple[dict[str, int], list[Demand]]:
    """The count of rounds each blocked label has stood blocked, and the needs of those still within `label_recut_limit` recuts.

    A label past its limit is asked for no more, so the loop settles and its LABEL_NO_ROOM finding stands (R2486).
    """
    needs = [d for p in routes.pages for d in p.needs]
    tried = {**tried, **{o: tried.get(o, 0) + 1 for o in {d.owner for d in needs if d.owner}}}
    return tried, [d for d in needs if tried.get(d.owner, 0) <= options.label_recut_limit]


def tagged_by(problem: PlacementProblem, lost: Iterable[Refused], apart: Iterable[Refused] = (), legless: Iterable[PinRef] = ()) -> PlacementProblem:
    """The problem whose nets hold each lost link as a tagged one (layout-0508) and each apart pair as an apart one (layout-0635).

    The cut plans their tag pairs, so placement reserves their room.
    A pin whose leg stood no line is `legless`: the next cut ends it at the trunk end.
    """
    out = problem
    for field, refused in (("tagged", lost), ("apart", apart)):
        held = {n.id: set(getattr(n, field)) for n in out.nets}
        by_net: dict[str, list[tuple[PinRef, ...]]] = {}
        for r in refused:
            if r.ends and len(r.ends) > 1 and r.ends not in held.get(r.net, ()) and r.ends not in by_net.get(r.net, ()):
                by_net.setdefault(r.net, []).append(r.ends)
        if by_net:
            out = replace(out, nets=tuple(replace(n, **{field: (*getattr(n, field), *by_net[n.id])}) if n.id in by_net else n for n in out.nets))
    new = {p for p in legless if all(p not in n.legless for n in out.nets)}
    if new:
        out = replace(out, nets=tuple(replace(n, legless=(*n.legless, *(p for p in n.pins if p in new))) for n in out.nets))
    return out


def floored(routes: Routes) -> Routes:
    """The routes with each page's label needs read as demands: the gap beside a blocked label is wanted as wide as the label (T6)."""
    pages = []
    for p in routes.pages:
        want: dict[str, int] = {}
        for d in (*p.demand, *p.needs):
            if d.room:
                continue
            want[d.gap] = max(want.get(d.gap, 0), d.tracks)
        pages.append(replace(p, demand=tuple(Demand(g, t) for g, t in want.items())))
    return replace(routes, pages=tuple(pages))


def asked_of(demands: Iterable[Demand], given: Mapping[tuple[str, str], Demand]) -> tuple[list[Demand], dict[tuple[str, str], Demand]]:
    """The room and rung boxes each owner is asked for, per side, beyond what an earlier pass gave (layout-0559, R1831, R1961)."""
    want: dict[tuple[str, str], Demand] = {}
    for d in demands:
        if d.owner and (d.room or d.box):
            old = want.get((d.owner, d.side), Demand("", 0, owner=d.owner, side=d.side))
            box = d.box if old.box is None or d.box is None else union(old.box, d.box)
            want[d.owner, d.side] = Demand("", 0, max(old.room, d.room), d.owner, box=box or old.box, side=d.side)
    asked = []
    for k, w in want.items():
        g = given.get(k, Demand("", 0, owner=k[0], side=k[1]))
        if w.room > g.room or (w.box is not None and w.box != g.box):
            asked.append(Demand("", 0, w.room - g.room if w.room > g.room else 0, k[0], box=w.box if w.box != g.box else None, side=k[1]))
    return asked, {**given, **want}


def digits_of(placement: Placement, problem: PlacementProblem, risen: int) -> tuple[PlacementProblem, int, bool]:
    """`problem` with the annexes for the digits of the page count, once they pass the `risen` reserved; digits only rise (R1883)."""
    rise = len(problem.wider[: len(str(len(placement.pages))) - 1])  # capped at the sets `wider` holds
    return (replace(problem, annexes=problem.wider[rise - 1]), rise, True) if rise > risen else (problem, risen, False)
