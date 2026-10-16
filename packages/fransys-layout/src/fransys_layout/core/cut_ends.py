"""Stage 4: the row and the pin of each reference end the cut plans (layout-0292).

`ref_pins` lists the pins a fan or net names, each with its position in the unit's sequence. An
end names the pin of its reference on its page nearest the end's own position, ties by
`natural_key`; an end whose page holds none names no pin.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import replace
from typing import TYPE_CHECKING

from .cut_costs import ref_name
from .keys import natural_key
from .ref_kind import kind_of
from .values import Ref, RefEnd

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .cut_dp import Plan, RowState
    from .values import Attach, FlowGraph, PinRef

Placed = tuple[tuple[int, "PinRef"], ...]


def _placed(ends: Sequence[Attach], pos: Mapping[str, int]) -> Placed:
    """The pins of `ends` that stand in this unit's sequence, as the cut's span counts them."""
    return tuple((pos[n], a.pin) for a in ends if (n := a.column or a.pin.sym) in pos)


def ref_pins(flow: FlowGraph, pos: Mapping[str, int]) -> dict[str, Placed]:
    """Every pin a fan or a cross link names, with its position in the sequence."""
    out = {ref_name(f): _placed((*f.drivers, *f.legs), pos) for f in flow.fans}
    out.update({link.net: _placed(link.ends, pos) for link in flow.cross_links})
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
    return {
        q: bisect_right(row_starts(state), q)
        for first, last, state in plan
        for q in range(first, last + 1)
    }


def end_at(
    at: int, column: str, placed: Placed, page_of: Mapping[int, int], row_of: Mapping[int, int]
) -> RefEnd:
    """The end of a reference at position `at`, whose column is `column`."""
    page = page_of[at]
    near = [
        (abs(i - at), natural_key(p.sym), natural_key(p.pin), p)
        for i, p in placed
        if page_of[i] == page
    ]
    pin = min(near, key=lambda n: n[:3])[3] if near else None
    return RefEnd(page, column, pin, row_of[at])


def _meets_pinless(prev: Ref, ref: Ref) -> bool:
    """True when `prev` ends on the page `ref` starts on, and its end there names no pin."""
    return prev.ends[1].pin is None and prev.ends[1].page == ref.ends[0].page


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
        if key in last and (prev := out[last[key]]) is not None and _meets_pinless(prev, ref):
            kept = replace(ref, ends=(prev.ends[0], ref.ends[1]))
            out[last[key]] = None
        last[key] = len(out)
        out.append(kept)
    return [r for r in out if r is not None]
