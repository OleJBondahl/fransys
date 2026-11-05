"""The reference that stands in for each conductor the router lost (ROUTE-FALLBACK-REFERENCE)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .net_keys import net_of_key
from .outputs import Refused
from .values import Finding, Ref, RefEnd, RefKind

if TYPE_CHECKING:
    from collections.abc import Iterable

    from .flow_values import CutResult
    from .outputs import Placement
    from .values import PlacementProblem


def fallback(cut: CutResult, placement: Placement, lost: Iterable[Refused]) -> tuple[Ref, ...]:
    """A tag pair on the two pins of each lost link or jog, a one-sided stub at the pin of a lost drop (A15)."""
    page_of = {p.sym: pg.page for pg in placement.pages for p in pg.placed}
    column_of = {c.sym: col.id for col in cut.flow.columns for lane in col.lanes for c in lane.cells}
    out: list[Ref] = []
    for r in lost:
        pins = r.ends or ()
        if pins:
            two = len(pins) > 1
            ends = tuple(RefEnd(page_of[p.sym], column_of.get(p.sym) if two else None, p) for p in pins)
            out.append(Ref(net_of_key(r.net), RefKind.TAG if two else RefKind.STUB, ends))
    return tuple(out)


def handed(cut: CutResult, placement: Placement, problem: PlacementProblem) -> tuple[Ref, ...]:
    """The fallback references of the links `widen` handed to the cut (`Net.tagged`): announced like the loop's own."""
    return fallback(cut, placement, (Refused(n.id, t) for n in problem.nets for t in n.tagged))


def announced(refs: Iterable[Ref]) -> tuple[Finding, ...]:
    """One INFO WIRE_AS_REFERENCE per fallback reference, naming the net and the pins it stands at."""
    out = []
    for ref in refs:
        pins = ", ".join(f"{e.pin.sym}.{e.pin.pin}" for e in ref.ends if e.pin)
        text = f"net {ref.net} has no free path between {pins}, so it is drawn as a reference at each"
        out.append(Finding("WIRE_AS_REFERENCE", text, ref.ends[0].page, ref.net))
    return tuple(out)
