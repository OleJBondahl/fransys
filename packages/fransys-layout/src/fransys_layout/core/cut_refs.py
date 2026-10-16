"""Stage 4, after the DP: the references the cut plans, and the findings it reports.

Arrows and tags per cut, a tag for each column spilled off a card, a copy of a free-sided hub on
each other page of its fan, the P3 check (HEAD_OFF_LEGS) and a stub at each unit boundary pin.
`Fan.crossed` is neither read nor filled (layout-0275).
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from .cut_costs import fan_columns
from .cut_ends import Placed, end_at, link_over_pinless, row_starts, rows_of
from .fan_head import fan_head, head_short
from .keys import natural_key
from .topology_elements import is_free_sided
from .values import Finding, Ref, RefEnd, RefKind

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .cut_dp import Cut, Plan
    from .values import BlockList, Column, Fan, FlowGraph, Net, PinRef, PlacementProblem


def copyable_fans(flow: FlowGraph, problem: PlacementProblem) -> frozenset[str]:
    """Fans whose hub is a free-sided symbol: it may be drawn again on each page the fan reaches."""
    syms = {s.id: s for s in problem.symbols}
    return frozenset(f.id for f in flow.fans if f.hub is not None and is_free_sided(syms[f.hub]))


def references(
    cut: Cut,
    plan: Plan,
    page_of: Mapping[int, int],
    copyable: frozenset[str],
    pins: Mapping[str, Placed],
) -> list[Ref]:
    """One arrow pair per trunk per cut it crosses, one tag pair per cut two-pin net.

    A page cut through a trunk with a free-sided hub plans no arrow: the hub is copied instead.
    Each end carries its row and the pin of the reference nearest it on its page (cut_ends).
    """
    row_of = rows_of(plan)
    row_cuts = {s - 1 for _, _, state in plan for s in row_starts(state)}
    page_cuts = {k for _, k, _ in plan[:-1]}
    out: list[Ref] = []
    for b in sorted(row_cuts | page_cuts):
        for kind, names in ((RefKind.ARROW, cut.bounds[b].fans), (RefKind.TAG, cut.bounds[b].nets)):
            for name in names:
                if kind is RefKind.ARROW and b in page_cuts and name in copyable:
                    continue
                ends = tuple(
                    end_at(q, cut.seq[q].column, pins[name], page_of, row_of) for q in (b, b + 1)
                )
                out.append(Ref(name, kind, ends))
    return link_over_pinless(out)


def on_pages(ref: Ref, where: Mapping[str, int]) -> Ref:
    """A reference planned before the DP, its ends put on the pages their columns came to."""
    return replace(ref, ends=tuple(replace(e, page=where[e.column or ""]) for e in ref.ends))


def _column_pin(column: Column, net: Net) -> PinRef:
    """The first pin, in the order of its ids, that `net` has on a cell of `column`."""
    cells = {x.sym for ln in column.lanes for x in ln.cells}
    on = [p for p in net.pins if p.sym in cells]
    if not on:
        msg = (
            f"cut: net {net.id}: spilled column {column.id} holds none of its pins; "
            "a spilled tag is planned only for a column that holds a pin of the net"
        )
        raise ValueError(msg)
    return min(on, key=lambda p: (natural_key(p.sym), natural_key(p.pin)))


def spilled(
    blocks: Sequence[BlockList],
    flow: FlowGraph,
    where: Mapping[str, int],
    problem: PlacementProblem,
) -> list[Ref]:
    """A column that left its box's card (CARD_OVERFULL) is tied to its box pin by one tag pair.

    The net is an attachment, not a fan, so the DP never sees it; the tag is paid whatever the cut.
    """
    columns = {c.id: c for c in flow.columns}
    nets = {n.id: n for n in problem.nets}
    out: list[Ref] = []
    for unit in blocks:
        for col in (c for b in unit.blocks if b.kind == "column" for c in b.columns):
            for end in (*columns[col].heads, *columns[col].feet):
                if end.kind == "boxpin" and end.pin is not None:
                    pin = _column_pin(columns[col], nets[end.net or ""])
                    ends = (
                        RefEnd(where[col], col, pin),
                        RefEnd(where[end.pin.sym], None, end.pin),
                    )
                    out.append(Ref(end.net or "", RefKind.TAG, ends))
    return out


def _fan_pages(fan: Fan, where: Mapping[str, int]) -> set[int]:
    return {where[n] for n in fan_columns(fan) if n in where}


def _page_pin(fan: Fan, page: int, where: Mapping[str, int]) -> PinRef | None:
    """The fan's first pin, in the order of its ids, that stands on `page`."""
    on = [a.pin for a in (*fan.drivers, *fan.legs) if where.get(a.column or a.pin.sym) == page]
    return min(on, key=lambda p: (natural_key(p.sym), natural_key(p.pin))) if on else None


def copies(flow: FlowGraph, where: Mapping[str, int], copyable: frozenset[str]) -> list[Ref]:
    """One copy per copyable fan on two or more pages, an end on each page beyond the hub's.

    The hub is on another page, so an end names the fan's first pin on its own page.
    """
    out: list[Ref] = []
    for fan in (f for f in flow.fans if f.id in copyable):
        pages = _fan_pages(fan, where)
        if len(pages) > 1:
            hub = next(a.column for a in (*fan.drivers, *fan.legs) if a.pin.sym == fan.hub)
            ends = tuple(
                RefEnd(p, hub, _page_pin(fan, p, where)) for p in sorted(pages - {where[hub or ""]})
            )
            out.append(Ref(fan.nets[0], RefKind.COPY, ends))
    return out


def head_off_legs(flow: FlowGraph, where: Mapping[str, int]) -> tuple[Finding, ...]:
    """P3, reported and not repaired: the head's page holds fewer legs than another page."""
    out: list[Finding] = []
    for fan in flow.fans:
        head = fan_head(fan)
        if head is None or (page := where.get(head.column or head.pin.sym)) is None:
            continue
        legs = [where[n] for a in fan.legs if (n := a.column or a.pin.sym) in where]
        if (short := head_short({page}, legs)) is not None:
            text = f"{fan.id}: head on page {page} holds {short[0]} of its legs, "
            text += f"page {short[1]} holds {short[2]}"
            out.append(Finding("HEAD_OFF_LEGS", text, page, fan.id))
    return tuple(out)


def stubs(problem: PlacementProblem, where: Mapping[str, int]) -> list[Ref]:
    """A net that crosses units ends in a stub at each unit boundary pin of it; stubs cost 0."""
    boundary = {p for u in problem.facts.units for p in u.boundary}
    out: list[Ref] = []
    for net in (n for n in problem.nets if n.crosses_unit):
        ends = tuple(
            RefEnd(where[p.sym], None, p) for p in net.pins if p in boundary and p.sym in where
        )
        if ends:
            out.append(Ref(net.id, RefKind.STUB, ends))
    return out
