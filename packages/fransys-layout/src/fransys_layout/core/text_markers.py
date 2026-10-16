"""Stage 8a: one Marker for each end of each planned reference, placed from the placement alone.

Ends of a reference go in the order (page, row of the column, pin); every tie breaks by
`natural_key`. A marker names the cell of the far end: the first other end of its reference, or
the hub itself for a copy. It reads no `Routes`; the text printed beside it is the builder's.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

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
    """The place the marker at end i names: the hub of a copy, else the first other end."""
    if kind_of(ref) is RefKind.COPY:
        return hub_xy(env, ref, end)
    other = stands[0] if i else stands[min(1, len(stands) - 1)]
    return other.x, other.y


def mark_ref(env: MarkEnv, ref: Ref) -> list[Marker]:
    """One marker for each end of `ref`, in the order of its ends."""
    ends = sorted(ref.ends, key=lambda e: _order(ref, e))
    stands = [end_stand(env, ref, e, i) for i, e in enumerate(ends)]
    out = []
    for i, (end, st) in enumerate(zip(ends, stands, strict=True)):
        cell = cell_of(*_far(env, ref, stands, end, i), env.area, env.options.cells)
        out.append(Marker(ref.net, kind_of(ref), end.page, cell, st.x, st.y, st.end))
    return out


def mark_pages(
    cut: CutResult, placement: Placement, problem: PlacementProblem, options: Options
) -> tuple[Marker, ...]:
    """The markers of every reference in the cut's plan, in the plan's order."""
    env = mark_env(cut, placement, problem, options)
    return tuple(m for ref in cut.spec.reference_plan for m in mark_ref(env, ref))
