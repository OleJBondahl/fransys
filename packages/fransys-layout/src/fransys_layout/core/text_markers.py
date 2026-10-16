"""Stage 8a: one Marker for each end of each planned reference, placed from the placement alone.

Ends of a reference go in the order (page, row of the column, pin); every tie breaks by
`natural_key`. A marker names the cell of the far end: the next end of its reference in that
order, cyclically (layout-0296), or the hub itself for a copy. Markers on one side of one row whose
boxes overlap along the edge take `intervals.levels`, one box further out per level. It reads no
`Routes`; the text printed beside it is the builder's.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from . import intervals
from .geometry import marker_box, marker_box_at, overlaps
from .keys import natural_key
from .outputs import Marker
from .ref_kind import kind_of
from .text_cells import cell_of
from .text_ends import end_stand, hub_xy, mark_env, who
from .values import RefKind

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .outputs import Placement
    from .text_ends import MarkEnv, Stand
    from .values import CutResult, Options, PlacementProblem, Ref, RefEnd


def _order(ref: Ref, end: RefEnd) -> tuple[object, ...]:
    """The sort key of an end; an end with no pin, or an arrow end with no row, is refused."""
    if end.pin is None or (end.row is None and kind_of(ref) is RefKind.ARROW):
        what = "pin" if end.pin is None else "row"
        msg = (
            f"marks: {who(ref)} page {end.page}: the end names no {what}; "
            "stage 4 fills RefEnd.row and pin"
        )
        raise ValueError(msg)
    row = () if end.row is None else (end.row,)  # a stub, copy or spilled tag stands in no row
    return end.page, row, natural_key(end.column or ""), natural_key(f"{end.pin.sym}.{end.pin.pin}")


def _far(env: MarkEnv, ref: Ref, stands: Sequence[Stand], end: RefEnd, i: int) -> tuple[int, int]:
    """The place the marker at end i names: the hub of a copy, else the next end, cyclically."""
    if kind_of(ref) is RefKind.COPY:
        return hub_xy(env, ref, end)
    other = stands[(i + 1) % len(stands)]
    return other.x, other.y


def stand_ref(env: MarkEnv, ref: Ref) -> list[tuple[Marker, Stand]]:
    """One marker and its stand for each end of `ref`, in the order of its ends."""
    ends = sorted(ref.ends, key=lambda e: _order(ref, e))
    stands = [end_stand(env, ref, e, i) for i, e in enumerate(ends)]
    out = []
    for i, (end, st) in enumerate(zip(ends, stands, strict=True)):
        cell = cell_of(*_far(env, ref, stands, end, i), env.area, env.options.cells)
        mk = Marker(ref.net, kind_of(ref), end.page, cell, st.x, st.y, st.end, st.orient)
        out.append((mk, st))
    return out


def _along_x(st: Stand) -> bool:
    """A marker above or below its end lines up along x; one beside it, along y."""
    return st.side in "NS"


def _span(m: Marker, st: Stand, options: Options) -> tuple[int, int]:
    b = marker_box(m, options)
    return (b.x, b.x + b.w) if _along_x(st) else (b.y, b.y + b.h)


def _moved(m: Marker, st: Stand, level: int, options: Options) -> Marker:
    """The marker `level` boxes further out on its side."""
    box = marker_box_at(0, 0, options, m.orient)
    sign = 1 if st.side in "ES" else -1
    if _along_x(st):
        return replace(m, y=m.y + sign * level * box.h)
    return replace(m, x=m.x + sign * level * box.w)


def stagger(pairs: Sequence[tuple[Marker, Stand]], options: Options) -> list[Marker]:
    """Markers on one side of one row that overlap along the edge stand one box further out each.

    A row's side is a page, a turned side and the coordinate across it; the order is the position
    along it. The levels are `intervals.levels` over the boxes (touching overlaps).
    """
    groups: dict[tuple[object, ...], list[int]] = {}
    for i, (m, st) in enumerate(pairs):
        across = m.y if _along_x(st) else m.x
        groups.setdefault((m.page, st.side, across), []).append(i)
    out = [m for m, _ in pairs]
    for idx in groups.values():
        idx.sort(key=lambda i: out[i].x if _along_x(pairs[i][1]) else out[i].y)
        spans = [_span(*pairs[i], options) for i in idx]
        for i, lv in zip(idx, intervals.levels(spans, range(len(idx))), strict=True):
            out[i] = _moved(*pairs[i], lv, options)
    return _cleared(out, [st for _, st in pairs], options)


def _first_hit(out: Sequence[Marker], options: Options) -> tuple[int, int] | None:
    """The first pair (earlier, later) of one page whose boxes overlap, else None."""
    return next(
        (
            (i, j)
            for j in range(len(out))
            for i in range(j)
            if out[i].page == out[j].page
            and overlaps(marker_box(out[i], options), marker_box(out[j], options))
        ),
        None,
    )


def _cleared(placed: Sequence[Marker], stands: Sequence[Stand], options: Options) -> list[Marker]:
    """Markers of different sides that still overlap: the later one steps one box further out.

    A copy at a pin and an arrow at the trunk end can meet; each step is the stagger's own. When
    the rounds run out with an overlap left, it raises: the overlap is never kept silently.
    """
    out = list(placed)
    for _ in out:
        if (hit := _first_hit(out, options)) is None:
            return out
        out[hit[1]] = _moved(out[hit[1]], stands[hit[1]], 1, options)
    if (hit := _first_hit(out, options)) is not None:
        a, b = out[hit[0]], out[hit[1]]
        msg = (
            f"marks: page {b.page}: markers {a.net} at ({a.x}, {a.y}) and "
            f"{b.net} at ({b.x}, {b.y}) still overlap after {len(out)} rounds of "
            "stepping outward; give the page more room beside them or a smaller Options.marker"
        )
        raise ValueError(msg)
    return out


def mark_pages(
    cut: CutResult, placement: Placement, problem: PlacementProblem, options: Options
) -> tuple[Marker, ...]:
    """The markers of every reference in the cut's plan, in the plan's order, staggered."""
    env = mark_env(cut, placement, problem, options)
    return tuple(
        stagger([p for ref in cut.spec.reference_plan for p in stand_ref(env, ref)], options)
    )
