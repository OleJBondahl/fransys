"""The annex stage: boxes printed beside a placed symbol, set after the symbols and wires (R345).

An `Annex` is a box of known size with named spots relative to its owner's placed body.
Annexes with the same `stack` and spot name stack by `grow`, in the order given. The core sorts
nothing and invents no size or spot: the caller measures both.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from itertools import pairwise
from typing import TYPE_CHECKING, NamedTuple

from .annex_values import AnnexBox
from .clearance import Keep, clear
from .errors import CoreError
from .geometry import around, inside, overlaps
from .outputs import Demand
from .values import Box, Finding

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from .annex_values import Annex, Spot
    from .outputs import Placed, Wire
    from .values import Size


def _wire_x(placed: Placed, spot: Spot) -> int | None:
    """The x of the wire the box keeps beside: the outermost pin on the spot's body edge."""
    body = placed.body
    edge = body.y + body.h if spot.corner[0] == "B" else body.y
    xs = [p.x for p in placed.pin_xy if p.y == edge]
    return (max(xs) if spot.corner[1] == "R" else min(xs)) if xs else None


def spot_box(placed: Placed, size: Size, spot: Spot, used: int) -> Box:
    """The annex's box at `spot`; `used` is the height the stack holds before it."""
    body = placed.body
    right = spot.corner[1] == "R"
    x = body.x + (body.w if right else 0) + spot.dx
    y = body.y + (body.h if spot.corner[0] == "B" else 0) + spot.dy
    y += used if spot.grow == "down" else -used
    wire = _wire_x(placed, spot) if spot.clear else None
    if wire is not None:
        x = max(x, wire + spot.clear) if right else min(x, wire - spot.clear - size.w)
    return Box(x, y, size.w, size.h)


def _size(annex: Annex, spot: Spot) -> Size:
    """The size of `annex` at `spot`: the measured turned size for a turned spot."""
    if not spot.turned:
        return annex.size
    if annex.turned is None:
        msg = f"annex of {annex.owner} has a turned spot {spot.name} but no turned size: pass Annex.turned from the symdef layer"
        raise CoreError(msg)
    return annex.turned


def _candidates(annexes: Sequence[Annex], owners: Mapping[str, Placed]) -> list[list[Cand]]:
    """(spot, box) per annex in preference order; stacked annexes sit past the heights before."""
    held: dict[tuple[str, str | None, str], int] = {}
    out = []
    for annex in annexes:
        placed = owners[annex.owner]
        spots = annex.spots.get(placed.orient)
        if not spots:
            msg = f"annex of {annex.owner} has no spot at {placed.orient}: pass spots for each turn"
            raise CoreError(msg)
        keys = [(annex.owner, annex.stack, s.name) for s in spots]
        used = [held.get(k, 0) if annex.stack is not None else 0 for k in keys]
        out.append([Cand(s.name, spot_box(placed, _size(annex, s), s, u), s.turned) for s, u in zip(spots, used, strict=True)])
        for k, u in zip(keys, used, strict=True):
            held[k] = u + annex.size.h
    return out


def _wire_keeps(wires: Sequence[Wire]) -> list[Keep]:
    """One keep per wire segment, its true extent."""
    return [
        Keep("", Box(min(ax, bx), min(ay, by), abs(bx - ax), abs(by - ay)), "wire", w.net) for w in wires for (ax, ay), (bx, by) in pairwise(w.points)
    ]


def _clear(box: Box, keeps: Sequence[Keep]) -> bool:
    """Whether no keep shares interior with `box`: the box less its rim is the probe, so a touching edge is clear (`clearance.clear`)."""
    return not clear(Box(box.x + 1, box.y + 1, box.w - 2, box.h - 2), keeps, {})


class Cand(NamedTuple):
    """One candidate of an annex: its spot's name, its box and whether the box is turned."""

    name: str
    box: Box
    turned: bool


Cands = Sequence[Cand]
Ink = tuple[Sequence[Keep], Sequence[Keep]]


def _solid(box: Box) -> Keep:
    return Keep("", box, "text", "")


def _free(box: Box, ink: Ink, area: Size | None) -> bool:
    """Whether a label stands at `box`: inside the content box and sharing no interior with a solid or a wire (TAG-CORNERS)."""
    return (area is None or inside(box, area)) and _clear(box, [*ink[0], *ink[1]])


def _first(spots: Cands, ink: Ink, on: tuple[Size | None, int]) -> Cand | None:
    """The first free candidate, one with a wire within the gap taken last (R1118); None when every one is blocked."""
    area, gap = on
    free = [s for s in spots if _free(s[1], ink, area)]
    return next((s for s in free if _clear(around(s[1], gap), ink[1])), free[0] if free else None)


def _move_out(hit: Sequence[int], box: Box, cands: Sequence[Cands], ink: Ink, on: tuple[Size | None, int]) -> list[tuple[int, AnnexBox]] | None:
    """Each label of `hit` at its first free candidate with `box` taken; None when one has none."""
    solids, wires = ink
    moved = []
    for j in hit:
        found = _first(cands[j], ([*solids, _solid(box), *(_solid(m[1].box) for m in moved)], wires), on)
        if found is None:
            return None
        moved.append((j, AnnexBox("", 0, found.box, found.name, found.turned)))
    return moved


def _make_room(
    i: int,
    cands: Sequence[Cands],
    labels: Sequence[AnnexBox],
    held: tuple[Ink, Sequence[int]],
    on: tuple[Size | None, int, int],
) -> list[AnnexBox] | None:
    """The labels with annex i at a candidate where at most `moves` standing ones are, each moved to another free one: one step, never a search."""
    ink, blocked = held
    area, gap, moves = on
    for name, box, turned in cands[i]:
        hit = [j for j, a in enumerate(labels) if j not in blocked and j != i and overlaps(a.box, box)]
        if len(hit) > moves or not _free(box, ink, area):
            continue
        rest = [*ink[0], *(_solid(a.box) for j, a in enumerate(labels) if j not in blocked and j not in hit)]
        if (moved := _move_out(hit, box, cands, (rest, ink[1]), (area, gap))) is not None:
            out = list(labels)
            for j, to in moved:
                out[j] = replace(labels[j], box=to.box, spot=to.spot, turned=to.turned)
            out[i] = replace(labels[i], box=box, spot=name, turned=turned)
            return out
    return None


def _preferred(spots: Cands, prior: AnnexBox | None) -> list[Cand]:
    """The candidates with the box a label stood at the round before first: a label does not move without cause."""
    return [*(s for s in spots if prior and s[1] == prior.box), *(s for s in spots if not prior or s[1] != prior.box)]


def _greedy(
    annexes: Sequence[Annex],
    cands: Sequence[Cands],
    ink: Ink,
    on: tuple[int, Size | None, int],
    prior: Sequence[AnnexBox],
) -> tuple[list[AnnexBox], list[int]]:
    """Each annex at its first free candidate in order; a blocked one stands at its first inside the content box and is listed."""
    (static, wires), (page, area, gap) = ink, on
    labels: list[AnnexBox] = []
    blocked: list[int] = []
    for i, (annex, spots) in enumerate(zip(annexes, cands, strict=True)):
        ordered = _preferred(spots, prior[i] if i < len(prior) else None)
        got = _first(ordered, ([*static, *(_solid(a.box) for j, a in enumerate(labels) if j not in blocked)], wires), (area, gap))
        stand = got or next((c for c in spots if area is None or inside(c[1], area)), spots[0])
        labels.append(AnnexBox(annex.owner, page, stand.box, stand.name, stand.turned))
        blocked += [] if got else [i]
    return labels, blocked


def _unplaced(annex: Annex, page: int, candidates: int) -> Finding:
    text = f"annex of {annex.owner} on page {page} is blocked at all {candidates} candidates: widen the gap beside it or shorten its text"
    return Finding("ANNEX_UNPLACED", text, page, annex.owner)


def _asks(annex: Annex, placed: Placed, first: Box) -> Demand:
    """What frees the annex's first rung: that rung's box, relative to the owner's origin, for the owner's footprint to hold (R1831)."""
    return Demand("", 0, owner=annex.owner, box=Box(first.x - placed.x, first.y - placed.y, first.w, first.h))


def place_labels(
    annexes: Sequence[Annex],
    placed: Mapping[str, Placed],
    ink: tuple[Sequence[Wire], Sequence[Box]],
    on: tuple[int, Size | None, int, int],
    prior: Sequence[AnnexBox] = (),
) -> tuple[list[AnnexBox], list[Finding], dict[int, Demand]]:
    """Each annex at its first free candidate; `ink` is the page's wires and solid boxes, `on` its page, content box, wire gap and MOVES (R1479).

    A label with none free makes room once, by moving the labels in its way; one still blocked stands at its first
    candidate inside the content box with ANNEX_UNPLACED and holds no room; its Demand, by index, is the first rung it needs freed.
    """
    (wires, boxes), (page, area, gap, moves) = ink, on
    keeps: Ink = ([_solid(b) for b in (*(p.body for p in placed.values()), *boxes)], _wire_keeps(wires))
    cands = _candidates(annexes, placed)
    labels, blocked = _greedy(annexes, cands, keeps, on[:3], prior)
    for i in list(blocked):
        roomed = _make_room(i, cands, labels, (keeps, blocked), (area, gap, moves))
        if roomed is not None:
            labels = roomed
            blocked.remove(i)
    rung = {i: next((c.box for c in cands[i] if area is None or inside(c.box, area)), cands[i][0].box) for i in blocked}
    asks = {i: _asks(annexes[i], placed[annexes[i].owner], rung[i]) for i in blocked}
    return labels, [_unplaced(annexes[i], page, len(cands[i])) for i in blocked], asks


def text_keeps(labels: Iterable[AnnexBox]) -> tuple[Keep, ...]:
    """Each label as a keep of kind "text" owned by its tag, not its symbol: the symbol's own markers keep clear of it too."""
    return tuple(Keep("", a.box, "text", f"{a.owner}:text") for a in labels)
