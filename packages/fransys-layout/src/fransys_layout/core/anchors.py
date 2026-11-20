"""Anchored items: a one-port item at a pin end reserves its outline and is placed with its owner.

The caller measures each Pose (turn, origin, outline) once; the core only moves it. Before
placement `reserved` joins the outline into the owner's views, so rows and columns leave room. After
it `anchor_pages` poses each item at its pin, and `anchor_misses` checks its outline.
"""

from __future__ import annotations

from dataclasses import replace
from functools import reduce
from itertools import pairwise
from types import MappingProxyType
from typing import TYPE_CHECKING, NamedTuple

from .annex import text_keeps
from .clearance import Keep, clear
from .geometry import marker_drawn_box, overlaps, shift, union
from .hang_levels import raised
from .hangings import hung_keeps
from .outline import outline_keeps
from .outputs import Anchored, Wire
from .values import Box, Finding, PinRef

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence
    from collections.abc import Set as AbstractSet

    from .annex_values import AnnexBox
    from .hangings import Hanging
    from .outputs import Marker, Outline, PagePlacement, Placed, Placement
    from .sym_values import Sym, Turned
    from .values import Anchor, Options, Orientation, PlacementProblem, Pose

__all__ = ("anchor_misses", "anchor_pages", "reserved")


def _frame(problem: PlacementProblem, options: Options) -> Box:
    m = options.margin
    return Box(m.w, m.h, problem.area.w - 2 * m.w, problem.area.h - 2 * m.h)


def _inside(box: Box, frame: Box) -> bool:
    return frame.x <= box.x and frame.y <= box.y and box.x + box.w <= frame.x + frame.w and box.y + box.h <= frame.y + frame.h


def _poses(anchor: Anchor, side: str) -> list[Pose]:
    return [p for s, p in anchor.poses if s == side]


def _unfit(a: Anchor, page: int) -> Finding:
    text = f"{a.pin.sym}/{a.pin.pin}: its item fits no pose clear of its surroundings; enlarge the page or split the unit"
    return Finding("PLACEMENT_PROBLEM", text, page, a.pin.sym)


def _index(sym: Sym, pin: str) -> int:
    return next(i for i, p in enumerate(sym.pins) if p.id == pin)


def _marker_keeps(page: int, markers: Sequence[Marker], options: Options) -> tuple[Keep, ...]:
    """The page's marker boxes as keeps (TRUNK-CLEAR item 3a)."""
    return tuple(Keep("", marker_drawn_box(m, options), "marker", m.end.sym, m.net, (m.x, m.y)) for m in markers if m.page == page)


def _anchor_keeps(page: int, anchored: Sequence[Anchored], net_of: Mapping[PinRef, str]) -> tuple[Keep, ...]:
    """The page's anchor outlines as keeps, each with the net of its pin."""
    return tuple(Keep("", o.outline, "anchor", o.sym, net_of.get(PinRef(o.sym, o.pin)), o.port) for o in anchored if o.page == page)


#: The kinds each reader of a page's keeps takes, in its order (TP1): the router's obstacles, a label's besides those, a marker's, an anchor's.
ROUTED = ("marker", "anchor", "hanging")
HELD = ("keepout", "body", "outline")
MARKED = ("wire", "text", "hanging", "outline", "anchor")
ANCHORED = ("body", "pin", "outline", "marker", "anchor")


def wire_keeps(wires: Iterable[Wire]) -> tuple[Keep, ...]:
    """One keep per wire segment, its true extent, owned by its net (R872, R1007)."""
    return tuple(
        Keep("", Box(min(ax, bx), min(ay, by), abs(bx - ax), abs(by - ay)), "wire", w.net, None, None, (w.points[0], w.points[-1]))
        for w in wires
        for (ax, ay), (bx, by) in pairwise(w.points)
    )


class Stood(NamedTuple):
    """What stands on a page besides its placement and hangings: the markers, anchors, frames, wires and labels that `page_keeps` turns into keeps."""

    markers: Sequence[Marker] = ()
    anchored: Sequence[Anchored] = ()
    outlines: Sequence[Outline] = ()
    wires: Iterable[Wire] = ()
    labels: Iterable[AnnexBox] = ()


def page_keeps(page: PagePlacement, stood: Stood, problem: PlacementProblem, options: Options, kinds: Sequence[str] = ROUTED) -> tuple[Keep, ...]:
    """The boxes a page holds, as keeps in the order of `kinds`: the one ledger every placer of a text, a marker, an anchor and a wire reads (TP1).

    A placer passes the kinds it keeps clear of: the router `ROUTED` (a wire crosses a frame), a marker its own frame by `own`.
    `keepout` is each symbol's slot ink (TP4); `outline` the frame edges and titles (TP3).
    """
    net_of = {ref: n.id for n in problem.nets for ref in n.pins} if "anchor" in kinds else {}
    ledger = {
        "marker": lambda: _marker_keeps(page.page, stood.markers, options),
        "anchor": lambda: _anchor_keeps(page.page, stood.anchored, net_of),
        "hanging": lambda: hung_keeps(page.hangings),
        "footprint": lambda: tuple(Keep("", p.footprint, "footprint", p.sym) for p in page.placed),
        "body": lambda: tuple(Keep("", p.body, "body", p.sym) for p in page.placed),
        "keepout": lambda: tuple(Keep("", p.keepout, "keepout", p.sym) for p in page.placed if p.keepout is not None),
        "pin": lambda: tuple(Keep("", Box(xy.x, xy.y, 0, 0), "pin", p.sym) for p in page.placed for xy in p.pin_xy),
        "outline": lambda: outline_keeps(stood.outlines, options.outline, page.page),
        "wire": lambda: wire_keeps(stood.wires),
        "text": lambda: text_keeps(stood.labels),
    }
    return tuple(k for kind in kinds for k in ledger[kind]())


# KI-1099: the first clear pose can sit in a neighbour pin's lane; POWER-POSE poses it clear of the lane.
def _fit(poses: Sequence[Pose], pin: tuple[int, int], taken: Sequence[Keep], frame: Box) -> Pose | None:
    """The first pose inside the frame meeting no keep in `taken`: the page's bodies, pins, frames, markers and the outlines posed before."""
    for pose in poses:
        box = shift(pose.outline, *pin)
        if _inside(box, frame) and not clear(box, taken, {}, edge="open"):
            return pose
    return None


def _hung(view: Turned, pin_at: tuple[int, int], rel: Box) -> Turned:
    """The view whose footprint also holds `rel` (a box from the pin) at the pin: the one fold."""
    box = shift(rel, *pin_at)
    row = view.row_footprint
    return replace(
        view,
        footprint=union(view.footprint, box),
        row_footprint=None if row is None else union(row, box),
    )


def _joined(view: Turned, pin_at: tuple[int, int], outline: Box) -> Turned:
    box = shift(outline, *pin_at)
    return replace(_hung(view, pin_at, outline), keepout=union(view.keepout, box))


def _anchored(syms: Mapping[str, Sym], anchors: Sequence[Anchor]) -> dict[str, Sym]:
    """Each anchor's deepest pose on a view's side joins that view's footprint in y (R392a)."""
    out = dict(syms)
    for a in anchors:
        if (sym := out.get(a.pin.sym)) is None:
            continue
        index, views = _index(sym, a.pin.pin), dict(sym.views)
        for orient, view in views.items():
            turn = view.pins[index]
            if poses := _poses(a, turn.side):
                deep = reduce(union, (p.outline for p in poses))
                tall = Box(view.footprint.x - turn.dx, deep.y, view.footprint.w, deep.h)
                views[orient] = _hung(view, (turn.dx, turn.dy), tall)
        out[a.pin.sym] = replace(sym, views=views)
    return out


def _flags(
    hangings: Mapping[tuple[str, str, Orientation], Sequence[Hanging]],
    placed: Mapping[str, Placed] | None,
    rows: Mapping[tuple[str, str], object],
) -> dict[object, list[tuple[str, str, Orientation, Hanging]]]:
    """The hangings that stagger together: one symbol's, or once placed, one row's (R565)."""
    out: dict[object, list[tuple[str, str, Orientation, Hanging]]] = {}
    for (sym_id, pin, orient), hs in hangings.items():
        if placed is not None and placed[sym_id].orient != orient:
            continue
        key = (sym_id, orient) if placed is None else rows.get((sym_id, pin), (sym_id, orient))
        out.setdefault(key, []).extend((sym_id, pin, orient, h) for h in hs if h.kind != "anchor")
    return out


def _pin_x(
    syms: Mapping[str, Sym],
    placed: Mapping[str, Placed] | None,
    item: tuple[str, str, Orientation, Hanging],
) -> int:
    """The pin's x for the stagger: its offset in its symbol, or once placed its x on the page."""
    sym_id, pin, orient, _ = item
    if placed is None:
        return syms[sym_id].views[orient].pins[_index(syms[sym_id], pin)].dx
    return next(p.x for p in placed[sym_id].pin_xy if p.pin == pin)


def _fold_one(sym: Sym, item: tuple[str, str, Orientation, Hanging], box: Box) -> Sym:
    _, pin, orient, _ = item
    view = sym.views[orient]
    turn = view.pins[_index(sym, pin)]
    return replace(sym, views={**sym.views, orient: _hung(view, (turn.dx, turn.dy), box)})


def folded(
    syms: Mapping[str, Sym],
    hangings: Mapping[tuple[str, str, Orientation], Sequence[Hanging]],
    anchors: Sequence[Anchor] = (),
    placed: Mapping[str, Placed] | None = None,
    rows: Mapping[tuple[str, str], object] = MappingProxyType({}),
) -> dict[str, Sym]:
    """`syms` whose views also hold the page's hangings at their pins (H4); poses are not fixed.

    Phase 1 (`placed` None) staggers a symbol's flags alone; phase 2 gives `placed` and `rows`,
    so a row's flags stagger together (R565). An anchor's hanging adds nothing: its pose folds.
    """
    out = dict(syms)
    for items in _flags(hangings, placed, rows).values():
        boxes = raised([(_pin_x(syms, placed, i), i[3]) for i in items])
        for item, box in zip(items, boxes, strict=True):
            out[item[0]] = _fold_one(out[item[0]], item, box)
    return _anchored(out, anchors)


def _sym_reserved(sym: Sym, anchors: Sequence[Anchor]) -> Sym:
    views = dict(sym.views)
    for anchor in anchors:
        index = _index(sym, anchor.pin.pin)
        for orient, view in views.items():
            turn = view.pins[index]
            if poses := _poses(anchor, turn.side):
                views[orient] = _joined(view, (turn.dx, turn.dy), poses[0].outline)
    return replace(sym, views=views)


def _owned(problem: PlacementProblem, missed: AbstractSet[tuple[str, str]]) -> dict[str, list[Anchor]]:
    """The anchors an owner holds: all of a non-card's, a card's only of `missed`."""
    cards = {s.id for s in problem.symbols if s.box is not None}
    by_sym: dict[str, list[Anchor]] = {}
    for a in problem.anchors:
        if a.pin.sym not in cards or (a.pin.sym, a.pin.pin) in missed:
            by_sym.setdefault(a.pin.sym, []).append(a)
    return by_sym


def reserved(problem: PlacementProblem, missed: AbstractSet[tuple[str, str]] = frozenset()) -> PlacementProblem:
    """The problem whose owners' views also hold their anchored outlines.

    A card holds only those of `missed` (owner, pin) pairs.
    """
    if not problem.anchors:
        return problem
    by_sym = _owned(problem, missed)
    syms = tuple(_sym_reserved(s, by_sym[s.id]) if s.id in by_sym else s for s in problem.symbols)
    return replace(problem, symbols=syms)


def _posed(a: Anchor, page: PagePlacement, at: Placed, pose: Pose) -> Anchored:
    pin = next(xy for xy in at.pin_xy if xy.pin == a.pin.pin)
    port = (pin.x + pose.port[0], pin.y + pose.port[1])
    origin = (pin.x + pose.origin[0], pin.y + pose.origin[1])
    outline = shift(pose.outline, pin.x, pin.y)
    return Anchored(a.pin.sym, a.pin.pin, page.page, *origin, pose.turn, outline, port, ((pin.x, pin.y), port))


def anchor_pages(
    placement: Placement,
    problem: PlacementProblem,
    options: Options,
) -> tuple[tuple[Anchored, ...], tuple[Finding, ...]]:
    """Each anchor posed at its owner's pin, clear of bodies, lines and earlier anchors; the markers stand after and clear it (R1786).

    An anchor that fits no pose is posed at its first and named by a PLACEMENT_PROBLEM finding.
    """
    syms = {s.id: s for s in problem.symbols}
    placed = {p.sym: (pg, p) for pg in placement.pages for p in pg.placed}
    pins = {a.pin: (xy.x, xy.y) for a in problem.anchors if a.pin.sym in placed for xy in placed[a.pin.sym][1].pin_xy if xy.pin == a.pin.pin}
    out: list[Anchored] = []
    found: list[Finding] = []
    for a in sorted((a for a in problem.anchors if a.pin in pins), key=lambda a: (pins[a.pin][1], pins[a.pin][0])):
        page, at = placed[a.pin.sym]
        sym = syms[a.pin.sym]
        if poses := _poses(a, sym.views[at.orient].pins[_index(sym, a.pin.pin)].side):
            taken = page_keeps(page, Stood((), out, placement.outlines), problem, options, ANCHORED)
            pose = _fit(poses, pins[a.pin], taken, _frame(problem, options))
            if pose is None:
                found.append(_unfit(a, page.page))
            out.append(_posed(a, page, at, pose or poses[0]))
    return tuple(out), tuple(found)


def _on_trunk(page: PagePlacement, at: tuple[int, int], step: int) -> bool:
    """Whether the point lies on a lane line of one of the page's trunks."""
    x, y = at
    return any(t.x0 <= x <= t.x1 and any(y == t.y + k * step for k in range(t.lanes)) for t in page.trunks)


def _hits(item: Anchored, page: PagePlacement, others: Sequence[Anchored], frame: Box, step: int) -> list[str]:
    box = item.outline
    hit = [p.sym for p in page.placed if overlaps(box, p.body)]
    hit += [o.sym + "/" + o.pin for o in others if o is not item and overlaps(box, o.outline)]
    hit += ["trunk"] * _on_trunk(page, item.port, step)
    return hit if _inside(box, frame) else [*hit, "frame"]


def anchor_misses(
    placement: Placement,
    anchored: tuple[Anchored, ...],
    problem: PlacementProblem,
    options: Options,
    markers: Sequence[Marker] = (),
) -> tuple[tuple[Anchored, list[str]], ...]:
    """Each anchored item whose outline meets a body, outline, marker or the frame, and what."""
    frame = _frame(problem, options)
    out: list[tuple[Anchored, list[str]]] = []
    for pg in placement.pages:
        mine = [a for a in anchored if a.page == pg.page]
        marks = _marker_keeps(pg.page, markers, options)
        for item in mine:
            hit = _hits(item, pg, mine, frame, options.wiring_grid)
            hit += ["marker"] * bool(clear(item.outline, marks, {}, edge="open"))
            if hit:
                out.append((item, hit))
    return tuple(out)


def anchor_leads(anchored: Sequence[Anchored]) -> tuple[Wire, ...]:
    """Each anchor's lead, pin to port, as a straight wire: route geometry the label stage keeps clear of, no obstacle to the router."""
    return tuple(Wire(o.sym, o.page, o.lead, "straight") for o in anchored)
