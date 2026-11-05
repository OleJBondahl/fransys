"""Stage 4: the row and the pin of each reference end the cut plans (layout-0292).

`ref_pins` lists the pins a fan or net names by lane, each with its position in the unit's
sequence. Both ends of a reference name pins of one lane (R544): the first lane, in the fan's
`nets` order, with a pin on each page the fan has pins on. An end names the pin of that lane on
its page nearest the end's own position, ties by `natural_key`; a page with none names no pin.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import replace
from typing import TYPE_CHECKING

from .cut_bundle import bundled
from .cut_costs import ref_name
from .errors import CoreError
from .keys import natural_key
from .ref_kind import kind_of
from .values import Ref, RefEnd, RefKind

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .cut_dp import Plan, RowState
    from .flow_values import Attach, Fan, FlowGraph
    from .values import PinRef

Placed = tuple[tuple[int, "PinRef"], ...]
Lanes = tuple[Placed, ...]


class ReferenceLaneError(CoreError):
    """Crossing lanes share no one lane that serves every page they have pins on."""


def _placed(ends: Sequence[Attach], pos: Mapping[str, int]) -> Placed:
    """The pins of `ends` that stand in this unit's sequence, as the cut's span counts them."""
    return tuple((pos[n], a.pin) for a in ends if (n := a.column or a.pin.sym) in pos)


def _lanes(fan: Fan, pos: Mapping[str, int]) -> Lanes:
    """The placed pins of each net of the fan, in the order of `fan.nets`."""
    ends = (*fan.drivers, *fan.legs)
    return tuple(_placed([a for a in ends if a.net == net], pos) for net in fan.nets)


def ref_pins(flow: FlowGraph, pos: Mapping[str, int]) -> dict[str, Lanes]:
    """Every pin a fan (by lane) or a cross link names, with its position in the sequence."""
    out = {ref_name(f): _lanes(f, pos) for f in flow.fans}
    out.update({link.net: (_placed(link.ends, pos),) for link in flow.cross_links})
    return out


def row_starts(state: RowState) -> list[int]:
    """The positions where a row of this page begins after its first, ascending."""
    out: list[int] = []
    st = state
    while st.prev is not None:
        out.append(st.start)
        st = st.prev
    return sorted(out)


def rows_of(plan: Plan) -> dict[int, int]:
    """The row, within its page, of each position the plan covers."""
    return {q: bisect_right(row_starts(state), q) for first, last, state in plan for q in range(first, last + 1)}


def end_at(at: int, column: str, placed: Placed, page_of: Mapping[int, int], row_of: Mapping[int, int]) -> RefEnd:
    """The end of a reference at position `at`, whose column is `column`."""
    page = page_of[at]
    near = [(abs(i - at), natural_key(p.sym), natural_key(p.pin), p) for i, p in placed if page_of[i] == page]
    pin = min(near, key=lambda n: n[:3])[3] if near else None
    return RefEnd(page, column, pin, row_of[at])


def lane_ends(
    name: str,
    lanes: Lanes,
    ats: Sequence[tuple[int, str]],
    page_of: Mapping[int, int],
    row_of: Mapping[int, int],
) -> tuple[RefEnd, ...]:
    """The two ends of a reference of `name`, both on one crossing lane.

    A cut that no lane crosses has no ends: the arrow is not planned (R547). A page where no
    crossing lane has a pin names none. Crossing lanes that split the pages raise (R545).
    """
    cut = ats[0][0]
    crossing = [ln for ln in lanes if ln and min(i for i, _ in ln) <= cut < max(i for i, _ in ln)]
    if not crossing:
        return ()
    held = [{page_of[i] for i, _ in ln} for ln in crossing]
    pages = {page_of[q] for q, _ in ats}
    needed = {pg for pg in pages if any(pg in h for h in held)}  # a page with no tap names no pin
    lane = next((ln for ln, h in zip(crossing, held, strict=True) if needed <= h), None)
    if lane is None:
        msg = (
            f"cut: reference {name}: lanes cross the cut but none has a pin on each of pages "
            f"{min(needed)} and {max(needed)}; an arrow joins one lane, so give the fan a lane "
            "with a pin on each page"
        )
        raise ReferenceLaneError(msg)
    maps = (page_of, row_of)
    return tuple(bundled(end_at(q, c, lane, *maps), [p for ln in crossing if ln is not lane if (p := end_at(q, c, ln, *maps).pin)]) for q, c in ats)


def link_over_pinless(refs: Sequence[Ref]) -> list[Ref]:
    """A page where a reference has no pin gets no end: the pages on either side are linked.

    Two refs of one name meet on a page whose end names no pin; they become one, from the first's
    left end to the second's right end.
    """
    out: list[Ref | None] = []
    last: dict[tuple[str, str], int] = {}
    for ref in refs:
        key = (ref.net, kind_of(ref))
        kept = ref
        if key in last and (prev := out[last[key]]) is not None and prev.ends[1].pin is None and prev.ends[1].page == ref.ends[0].page:
            kept = replace(ref, ends=(prev.ends[0], ref.ends[1]))
            out[last[key]] = None
        last[key] = len(out)
        out.append(kept)
    return [r for r in out if r is not None]


def link_over_empty_rows(refs: Sequence[Ref], rows: Mapping[str, frozenset[tuple[int, int]]]) -> list[Ref]:
    """An arrow end stands only in a (page, row) where its fan has a trunk (layout-0337).

    Two arrows of one fan meeting in a row with none become one; an arrow left with an end in
    such a row is dropped, the copy or the next page carrying the net.
    """
    out: list[Ref | None] = []
    last: dict[str, int] = {}
    for ref in refs:
        kept = ref
        if kind_of(ref) is RefKind.ARROW:
            prev = out[last[ref.net]] if ref.net in last else None
            if prev is not None and _meets_empty(prev, ref, rows[ref.net]):
                kept = replace(ref, ends=(prev.ends[0], ref.ends[1]))
                out[last[ref.net]] = None
            last[ref.net] = len(out)
        out.append(kept)
    return [r for r in out if r is not None and _stands(r, rows)]


def _empty(end: RefEnd, rows: frozenset[tuple[int, int]]) -> bool:
    return (end.page, end.row) not in rows


def _meets_empty(prev: Ref, ref: Ref, rows: frozenset[tuple[int, int]]) -> bool:
    return (prev.ends[1].page, prev.ends[1].row) == (ref.ends[0].page, ref.ends[0].row) and _empty(ref.ends[0], rows)


def _stands(ref: Ref, rows: Mapping[str, frozenset[tuple[int, int]]]) -> bool:
    if kind_of(ref) is not RefKind.ARROW:
        return True
    return not any(_empty(e, rows[ref.net]) for e in ref.ends)
