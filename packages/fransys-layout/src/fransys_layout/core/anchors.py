"""Anchored items: a one-port item at a pin end reserves its outline and is placed with its owner.

The caller measures each Pose (turn, origin, outline) once; the core only moves it. Before
placement `reserved` joins the outline into the owner's views, so rows and columns leave room. After
it `anchor_pages` poses each item at its pin, and `anchor_misses` checks its outline.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from .geometry import overlaps, shift, union
from .outputs import Anchored
from .values import Box

if TYPE_CHECKING:
    from collections.abc import Sequence
    from collections.abc import Set as AbstractSet

    from .outputs import PagePlacement, Placed, Placement
    from .sym_values import Sym, Turned
    from .values import Anchor, Options, PlacementProblem, Pose

__all__ = ("anchor_misses", "anchor_pages", "reserved")


def _frame(problem: PlacementProblem, options: Options) -> Box:
    m = options.margin
    return Box(m.w, m.h, problem.area.w - 2 * m.w, problem.area.h - 2 * m.h)


def _inside(box: Box, frame: Box) -> bool:
    return (
        frame.x <= box.x
        and frame.y <= box.y
        and box.x + box.w <= frame.x + frame.w
        and box.y + box.h <= frame.y + frame.h
    )


def _poses(anchor: Anchor, side: str) -> list[Pose]:
    return [p for s, p in anchor.poses if s == side]


def _index(sym: Sym, pin: str) -> int:
    return next(i for i, p in enumerate(sym.pins) if p.id == pin)


def _fit(
    poses: Sequence[Pose],
    pin: tuple[int, int],
    page: PagePlacement,
    taken: Sequence[Box],
    frame: Box,
) -> Pose:
    """The first pose inside the frame that meets no body, taken outline or pin, else the first."""
    stops = [*(p.body for p in page.placed), *taken]
    pins = [(xy.x, xy.y) for p in page.placed for xy in p.pin_xy]
    for pose in poses:
        box = shift(pose.outline, *pin)
        on_pin = any(box.x <= x <= box.x + box.w and box.y <= y <= box.y + box.h for x, y in pins)
        if _inside(box, frame) and not on_pin and not any(overlaps(box, b) for b in stops):
            return pose
    return poses[0]


def _joined(view: Turned, pin_at: tuple[int, int], outline: Box) -> Turned:
    box = shift(outline, *pin_at)
    return replace(
        view,
        keepout=union(view.keepout, box),
        footprint=union(view.footprint, box),
        row_footprint=None if view.row_footprint is None else union(view.row_footprint, box),
    )


def _sym_reserved(sym: Sym, anchors: Sequence[Anchor]) -> Sym:
    views = dict(sym.views)
    for anchor in anchors:
        index = _index(sym, anchor.pin.pin)
        for orient, view in views.items():
            turn = view.pins[index]
            if poses := _poses(anchor, turn.side):
                views[orient] = _joined(view, (turn.dx, turn.dy), poses[0].outline)
    return replace(sym, views=views)


def reserved(
    problem: PlacementProblem, missed: AbstractSet[tuple[str, str]] = frozenset()
) -> PlacementProblem:
    """The problem whose owners' views also hold their anchored outlines.

    A card holds only those of `missed` (owner, pin) pairs: the wires of its other pins enter
    through its footprint, so `solve` asks for them where the first pass left an outline astray.
    """
    if not problem.anchors:
        return problem
    cards = {s.id for s in problem.symbols if s.box is not None}
    by_sym: dict[str, list[Anchor]] = {}
    for a in problem.anchors:
        if a.pin.sym not in cards or (a.pin.sym, a.pin.pin) in missed:
            by_sym.setdefault(a.pin.sym, []).append(a)
    syms = tuple(_sym_reserved(s, by_sym[s.id]) if s.id in by_sym else s for s in problem.symbols)
    return replace(problem, symbols=syms)


def _posed(a: Anchor, page: PagePlacement, at: Placed, pose: Pose) -> Anchored:
    pin = next(xy for xy in at.pin_xy if xy.pin == a.pin.pin)
    port = (pin.x + pose.port[0], pin.y + pose.port[1])
    origin = (pin.x + pose.origin[0], pin.y + pose.origin[1])
    outline = shift(pose.outline, pin.x, pin.y)
    return Anchored(
        a.pin.sym, a.pin.pin, page.page, *origin, pose.turn, outline, port, ((pin.x, pin.y), port)
    )


def anchor_pages(
    placement: Placement, problem: PlacementProblem, options: Options
) -> tuple[Anchored, ...]:
    """Each anchor posed at its owner's pin on the owner's page, clear of what stands there."""
    syms = {s.id: s for s in problem.symbols}
    placed = {p.sym: (pg, p) for pg in placement.pages for p in pg.placed}
    frame = _frame(problem, options)
    out: list[Anchored] = []
    for a in problem.anchors:
        if a.pin.sym not in placed:
            continue
        page, at = placed[a.pin.sym]
        sym = syms[a.pin.sym]
        poses = _poses(a, sym.views[at.orient].pins[_index(sym, a.pin.pin)].side)
        if poses:
            pin = next(xy for xy in at.pin_xy if xy.pin == a.pin.pin)
            taken = [o.outline for o in out if o.page == page.page]
            out.append(_posed(a, page, at, _fit(poses, (pin.x, pin.y), page, taken, frame)))
    return tuple(out)


def _hits(item: Anchored, page: PagePlacement, others: Sequence[Anchored], frame: Box) -> list[str]:
    box = item.outline
    hit = [p.sym for p in page.placed if overlaps(box, p.body)]
    hit += [o.sym + "/" + o.pin for o in others if o is not item and overlaps(box, o.outline)]
    return hit if _inside(box, frame) else [*hit, "frame"]


def anchor_misses(
    placement: Placement,
    anchored: tuple[Anchored, ...],
    problem: PlacementProblem,
    options: Options,
) -> tuple[tuple[Anchored, list[str]], ...]:
    """Each anchored item whose outline meets a body, another outline or the frame, and what."""
    frame = _frame(problem, options)
    out: list[tuple[Anchored, list[str]]] = []
    for pg in placement.pages:
        mine = [a for a in anchored if a.page == pg.page]
        out += [(item, hit) for item in mine if (hit := _hits(item, pg, mine, frame))]
    return tuple(out)
