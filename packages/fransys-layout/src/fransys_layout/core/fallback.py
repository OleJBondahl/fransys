"""The reference that stands in for each conductor the router lost (ROUTE-FALLBACK-REFERENCE)."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from .net_keys import net_of_key
from .outputs import Refused
from .values import Finding, Ref, RefEnd, RefKind

if TYPE_CHECKING:
    from collections.abc import Iterable

    from .flow_values import CutResult
    from .outputs import Placement
    from .values import PinRef, PlacementProblem


def _named(plan: Iterable[Ref]) -> dict[PinRef, frozenset[PinRef]]:
    """Each pin a planned stub stands at, or also stands for, with the far pins that stub already names."""
    named: dict[PinRef, frozenset[PinRef]] = {}
    for r in plan:
        for e in r.ends if r.kind is RefKind.STUB else ():
            for p in (e.pin, *e.also):
                if p is not None:
                    named[p] = named.get(p, frozenset()) | frozenset(e.far)
    return named


def fallback(cut: CutResult, placement: Placement, lost: Iterable[Refused]) -> tuple[Ref, ...]:
    """A tag pair on the two pins of each lost link or jog, a one-sided stub at the pin of a lost drop (A15).

    A link with a pin whose stub does not yet name the link's other pins is drawn as a stub at each pin, the far ends joining the stub already there;
    where every stub at its pins names the others already, the tag pair stays.
    """
    page_of = {p.sym: pg.page for pg in placement.pages for p in pg.placed}
    column_of = {c.sym: col.id for col in cut.flow.columns for lane in col.lanes for c in lane.cells}
    held = _named(cut.spec.reference_plan)
    out: list[Ref] = []
    for r in lost:
        pins = r.ends or ()
        if pins:
            two = len(pins) > 1 and all(set(pins) - {p} <= held[p] for p in pins if p in held)
            ends = tuple(
                RefEnd(
                    page_of[p.sym], column_of.get(p.sym) if two else None, p, far=tuple(q for q in pins if q != p) if p in held and not two else ()
                )
                for p in pins
            )
            if two:
                out.append(Ref(net_of_key(r.net), RefKind.TAG, ends))
            else:
                out.extend(Ref(net_of_key(r.net), RefKind.STUB, (end,)) for end in ends)
    return tuple(out)


def with_refs(plan: Iterable[Ref], refs: Iterable[Ref]) -> tuple[Ref, ...]:
    """`plan` with `refs` added: a stub at a pin that already stands one adds its far ends to that stub, never a second marker."""
    plan = list(plan)
    at = {p: (i, j) for i, r in enumerate(plan) if r.kind is RefKind.STUB for j, e in enumerate(r.ends) for p in (e.pin,) if p is not None}
    extra: list[Ref] = []
    for ref in refs:
        end = ref.ends[0]
        if ref.kind is RefKind.STUB and end.pin in at and end.far:
            i, j = at[end.pin]
            old = plan[i].ends[j]
            ends = plan[i].ends
            plan[i] = replace(plan[i], ends=(*ends[:j], replace(old, far=tuple(dict.fromkeys((*end.far, *old.far)))), *ends[j + 1 :]))
        else:
            extra.append(ref)
    return (*plan, *extra)


def handed(cut: CutResult, placement: Placement, problem: PlacementProblem, drawn: Iterable[Ref]) -> tuple[Ref, ...]:
    """The fallback references of the links `widen` handed to the cut (`Net.tagged`) that a ref of `drawn` stands for: announced like the loop's."""
    shown = {(r.net, frozenset(e.pin for e in r.ends)) for r in drawn}
    refs = fallback(cut, placement, (Refused(n.id, t) for n in problem.nets for t in n.tagged))
    return tuple(r for r in refs if (r.net, frozenset(e.pin for e in r.ends)) in shown)


def announced(refs: Iterable[Ref]) -> tuple[Finding, ...]:
    """One INFO WIRE_AS_REFERENCE per fallback reference, naming the net and the pins it stands at."""
    out = []
    for ref in refs:
        pins = ", ".join(f"{e.pin.sym}.{e.pin.pin}" for e in ref.ends if e.pin)
        text = f"net {ref.net} has no free path between {pins}, so it is drawn as a reference at each"
        out.append(Finding("WIRE_AS_REFERENCE", text, ref.ends[0].page, ref.net))
    return tuple(out)
