"""Stage 8a: one Marker for each end of each planned reference, placed from the placement alone.

Ends of a reference go in the order (page, row of the column, pin); every tie breaks by
`natural_key`. A marker names the cell of the far end: the next end of its reference in that
order, cyclically (layout-0296), or the hub itself for a copy. Markers on one side of one row whose
boxes overlap along the edge take `intervals.stem_levels`, one box further out per level. It reads
no `Routes`; the text printed beside it is the builder's.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from .anchors import anchor_keeps
from .annex import text_keeps
from .clearance import clear, own_end
from .errors import CoreError
from .geometry import inset, inside, marker_box, marker_drawn_box
from .hang_levels import staggered
from .hangings import hung_keeps
from .keys import natural_key
from .net_keys import net_of_key
from .outline import outline_keeps
from .outputs import Marker
from .ref_kind import kind_of
from .stand_fit import Limits, fit
from .text_cells import cell_of
from .text_ends import bundle_nets, end_stand, hub_xy, mark_env, pin_keeps, who, wire_keeps
from .values import Box, Finding, RefKind

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .clearance import Keep
    from .flow_values import CutResult
    from .outputs import Placement
    from .route_fixed import Fixed
    from .text_ends import MarkEnv, Stand
    from .values import Options, PlacementProblem, Ref, RefEnd, Size

_LONE = frozenset({RefKind.STUB, RefKind.COPY})  # kinds whose ends stand and fail alone; any other keeps all its ends or none (R1566)


def _order(env: MarkEnv, ref: Ref, end: RefEnd) -> tuple[object, ...]:
    """The sort key of an end; an end with no pin, or an arrow end with no row, is refused."""
    if end.pin is None or (end.row is None and kind_of(ref) is RefKind.ARROW):
        what = "pin" if end.pin is None else "row"
        msg = f"marks: {who(ref)} page {end.page}: the end names no {what}; stage 4 fills RefEnd.row and pin"
        raise CoreError(msg)
    row = () if end.row is None else (end.row,)  # a stub, copy or spilled tag stands in no row
    column = env.columns[end.column] if end.column else ()
    return end.page, row, column, env.ranks[end.pin.sym], natural_key(end.pin.pin)


def _far(env: MarkEnv, ref: Ref, stands: Sequence[Stand], end: RefEnd, i: int) -> tuple[int, int]:
    """The place the marker at end i names: the hub of a copy, else the next end, cyclically."""
    if kind_of(ref) is RefKind.COPY:
        return hub_xy(env, ref, end)
    other = stands[(i + 1) % len(stands)]
    return other.x, other.y


def _inside(at: tuple[int, int], area: Size) -> tuple[int, int]:
    """The point held inside the area: a stand pushed past the page names its nearest cell."""
    return min(max(at[0], 0), area.w), min(max(at[1], 0), area.h)


def stand_ref(env: MarkEnv, ref: Ref) -> list[tuple[Marker, Stand]]:
    """One marker and its stand for each end of `ref`, in the order of its ends."""
    ends = sorted(ref.ends, key=lambda e: _order(env, ref, e))
    stands = [end_stand(env, ref, e, i) for i, e in enumerate(ends)]
    out = []
    for i, (end, st) in enumerate(zip(ends, stands, strict=True)):
        far = _far(env, ref, stands, end, i)
        cell = cell_of(*_inside(far, env.area), env.area, env.options.cells)
        mk = Marker(ref.net, kind_of(ref), end.page, cell, st.x, st.y, st.end, st.orient, ref.cut, end.also, end.far, end.stand)
        out.append((mk, st))
    return out


def _along_x(st: Stand) -> bool:
    """A marker above or below its end lines up along x; one beside it, along y."""
    return st.side in "NS"


def _moved(m: Marker, st: Stand, level: int, step: int) -> Marker:
    """The marker `level` steps further out on its side."""
    sign = 1 if st.side in "ES" else -1
    if _along_x(st):
        return replace(m, y=m.y + sign * level * step)
    return replace(m, x=m.x + sign * level * step)


def _toward(b: Box, at: tuple[int, int], side: str) -> bool:
    """True when a segment box `b` that ends at `at` runs out on `side`: into the marker's box, not away from it."""
    return {"N": b.y < at[1], "S": b.y + b.h > at[1], "W": b.x < at[0], "E": b.x + b.w > at[0]}[side]


def _fed(m: Marker, st: Stand, keeps: Mapping[int, Sequence[Keep]]) -> bool:
    """True for a marker a fixed wire arrives at from behind it: it never moves (R879).

    A boundary stub has no such wire: a wire that ends at its stand and runs on under its box is the pin's own (R920).
    """
    at = (m.x, m.y)
    return any(k.kind == "wire" and any(own_end(at, e) for e in k.ends) and not _toward(k.box, at, st.side) for k in keeps.get(m.page, ()))


def _slot(m: Marker, st: Stand, step: int, ctx: tuple[Options, Size, Mapping[int, Sequence[Keep]], Mapping[str, frozenset[str]]]) -> Marker | None:
    """The first slot from `m` outward whose box lies inside the page and on no other net's pin or lead end (R845).

    A boundary stub steps straight out along its pin's side until its box is clear (R920); a step lands on no other symbol's footprint.
    """
    options, area, keeps, own = ctx
    here = keeps.get(m.page, ())
    stand = [k for k in here if k.kind != "footprint"]  # the stand itself is as the placement left it
    framed = own.get(m.end.sym, frozenset())  # a marker of any kind stands on its own unit's frame line (R1104)
    owner = own.get(m.net, frozenset()) | framed | {m.end.sym}
    mine = frozenset({m.net, net_of_key(m.net), m.end.sym})  # a sibling fan's lane is exempt beside the box, never under it (R1063)
    fed, moved = _fed(m, st, keeps), False  # the wire that feeds a marker belongs to its stand, not to a slot
    bounds = Limits(area, st.band)
    if st.walked:  # walked clear of every keep at placement, the one fit test (R1331, R1338); no stand: no room (layout-0507)
        anchors = [k for k in here if k.kind == "anchor"]  # anchors stand after the placement that walked this stand (ANCHOR-FIRST)
        return m if st.stood and inside(marker_box(m, options), area) and fit(marker_box(m, options), anchors, owner, None) == () else None
    while (hit := fit(box := marker_box(m, options), here if moved else stand, owner, bounds, (m.x, m.y))) is not None:
        if not hit and not (m.kind == "stub" and clear(inset(box), [k for k in (here if moved else stand) if k.kind == "wire"], {}, own=mine)):
            return m
        if fed:
            return None
        m, moved = _moved(m, st, 1, step), True
    return None


def stagger(
    pairs: Sequence[tuple[Marker, Stand]],
    options: Options,
    area: Size,
    keeps: Mapping[int, Sequence[Keep]],
    own: Mapping[str, frozenset[str]],
) -> list[Marker | None]:
    """Markers on one side of one row that overlap along the edge stand one drawn box further out each.

    A slot outside `area` (R436) or on another net's pin or lead end (R845) is refused, the next
    one tried; none left is None. No other step; an overlap is counted (R453).
    """
    ctx = (options, area, keeps, own)
    got = staggered(
        [marker_drawn_box(m, options) for m, _ in pairs],
        [(m.page, st.side) for m, st in pairs],
        [m.x if _along_x(st) else m.y for m, st in pairs],
        [_along_x(st) for _, st in pairs],
    )
    return [_slot(_moved(m, st, 0 if _fed(m, st, keeps) else lv, step), st, step, ctx) for (m, st), (lv, step) in zip(pairs, got, strict=True)]


def _all_keeps(env: MarkEnv, placement: Placement, problem: PlacementProblem, options: Options, fixed: Mapping[int, Fixed]) -> dict[int, list[Keep]]:
    """Every page's keeps a marker clears: pins, fixed wires, the labels that stand, unit frames and anchor outlines."""
    keeps = pin_keeps(env)
    for page, more in wire_keeps(fixed).items():
        keeps.setdefault(page, []).extend(more)
    for page, pair in fixed.items():
        keeps.setdefault(page, []).extend(text_keeps(pair.labels))
    for pg in placement.pages:
        keeps.setdefault(pg.page, []).extend(hung_keeps(pg.hangings))
    for page in {o.page for o in placement.outlines}:
        keeps.setdefault(page, []).extend(outline_keeps(placement.outlines, options.outline, page))
    for page, more in anchor_keeps(placement, problem, options).items():
        keeps.setdefault(page, []).extend(more)
    return keeps


def placed_marks(
    cut: CutResult, placement: Placement, problem: PlacementProblem, options: Options, fixed: Mapping[int, Fixed]
) -> tuple[tuple[Marker, ...], tuple[Finding, ...]]:
    """The markers inside the page, in the plan's order, and MARKER_UNPLACED for each other.

    A slot on a fixed wire is refused as on another net's pin (R872). A pair (not a stub or copy) keeps all its ends or none and raises one
    MARKER_UNPLACED: an arrow by `Trunk.stood` (R1488), a tag or star here (R1566).
    """
    env = mark_env(cut, placement, problem, options)
    keeps = _all_keeps(env, placement, problem, options, fixed)
    env = replace(env, keeps=keeps)
    per_ref = [stand_ref(env, ref) for ref in cut.spec.reference_plan]
    own = {r.net: bundle_nets(env, r.net) for r in cut.spec.reference_plan}
    for key, members in problem.hints.frames:
        own.update({sym: own.get(sym, frozenset()) | {key} for sym in members})
    out = iter(stagger([p for ps in per_ref for p in ps], options, problem.area, keeps, own))
    kept: list[Marker] = []
    missed: list[Finding] = []
    for ref, ps in zip(cut.spec.reference_plan, per_ref, strict=True):
        got = [next(out) for _ in ps]
        missed += _missed(ref, ps, got)
        if kind_of(ref) in _LONE or None not in got:
            kept += [k for k in got if k is not None]
    return tuple(kept), tuple(missed)


def _missed(ref: Ref, ps: Sequence[tuple[Marker, Stand]], got: Sequence[Marker | None]) -> list[Finding]:
    """MARKER_UNPLACED for each end of a stub or copy that found no slot, and one for an arrow or star whatever its unstood ends (R1488)."""
    lone = [_unplaced(m) for (m, _), k in zip(ps, got, strict=True) if k is None]
    return lone if kind_of(ref) in _LONE else lone[:1]


def _unplaced(m: Marker) -> Finding:
    text = f"{m.kind} marker at {m.end.sym}/{m.end.pin}: no place inside page {m.page}"
    return Finding("MARKER_UNPLACED", text, m.page, f"{m.end.sym},{m.net}")
