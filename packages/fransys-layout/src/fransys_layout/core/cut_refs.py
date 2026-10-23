"""Stage 4, after the DP: the references the cut plans, and the findings it reports.

Arrows and tags per cut, a tag for each column spilled off a card, a copy of a free-sided hub on
each other page of its fan, the P3 check (HEAD_OFF_LEGS) and a stub at each unit boundary pin
and each page-alone end.
`Fan.crossed` is neither read nor filled (layout-0275).
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from .cut_costs import fan_columns
from .cut_ends import (
    Placed,
    end_at,
    link_over_empty_rows,
    link_over_pinless,
    row_starts,
    rows_of,
)
from .fan_head import fan_head, head_short
from .keys import natural_key
from .topology_elements import is_free_sided
from .values import Finding, PinRef, Ref, RefEnd, RefKind

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping, Sequence

    from .cut_dp import Cut, Plan
    from .values import BlockList, Column, Fan, FlowGraph, Net, PlacementProblem


def copyable_fans(flow: FlowGraph, problem: PlacementProblem) -> frozenset[str]:
    """Fans whose hub is a free-sided symbol: it may be drawn again on each page the fan reaches.

    A hub whose n and s pins are both unit boundary pins is not: its copy joins nothing for a
    reader, so the cut plans an arrow pair (PAGE-CUT, R455).
    """
    syms = {s.id: s for s in problem.symbols}
    boundary = {p for u in problem.facts.units for p in u.boundary}
    return frozenset(
        f.id
        for f in flow.fans
        if f.hub is not None
        and is_free_sided(syms[f.hub])
        and not {PinRef(f.hub, "n"), PinRef(f.hub, "s")} <= boundary
    )


def references(
    cut: Cut,
    plan: Plan,
    page_of: Mapping[int, int],
    copyable: frozenset[str],
    pins: Mapping[str, Placed],
) -> list[Ref]:
    """One arrow pair per trunk per cut it crosses, one tag pair per page-cut two-pin net.

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
                if kind is RefKind.TAG and b not in page_cuts:
                    continue  # rows.toml:98 one page one wire: a row cut keeps its wire, no tag
                ends = tuple(
                    end_at(q, cut.seq[q].column, pins[name], page_of, row_of) for q in (b, b + 1)
                )
                out.append(Ref(name, kind, ends))
    rows = {n: frozenset((page_of[i], row_of[i]) for i, _ in p) for n, p in pins.items()}
    return link_over_pinless(link_over_empty_rows(out, rows))


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


def _crossing(
    drawn: Sequence[PinRef],
    where: Mapping[str, int],
    boundary: Collection[PinRef],
    unit_of: Mapping[str, str | None],
) -> set[PinRef]:
    """The pins of a crossing net that stub: boundary pins and page-alone ends in units without."""
    pages = [where[p.sym] for p in drawn]
    held = {unit_of[p.sym] for p in drawn if p in boundary}
    alone = {p for p in drawn if pages.count(where[p.sym]) == 1 and unit_of[p.sym] not in held}
    return set(boundary) | alone


def _first_of_lines(
    problem: PlacementProblem, where: Mapping[str, int], skip: Collection[PinRef]
) -> list[Ref]:
    """One stub for each line of cut pins on a page, at the line's first pin (R481).

    The first is the first in the order of `problem.nets`, then of `net.cut`; the other conductors
    of the line run to that stub. A pin with no line is a line of its own.
    """
    lines: dict[tuple[int, str], tuple[str, PinRef]] = {}
    for net in problem.nets:
        for end in (c for c in net.cut if c.pin.sym in where and c.pin not in skip):
            line = end.line or f"{net.id}/{end.pin.sym}/{end.pin.pin}"
            lines.setdefault((where[end.pin.sym], line), (net.id, end.pin))
    return [
        Ref(net, RefKind.STUB, (RefEnd(page, None, pin),))
        for (page, _), (net, pin) in lines.items()
    ]


def fan_stubs(
    problem: PlacementProblem, flow: FlowGraph, where: Mapping[str, int]
) -> tuple[list[Ref], set[PinRef]]:
    """One stub per page for each bundle fan of cut ends alone on their nets (R499).

    It stands at the trunk end; the end names the fan's first such pin on its page.
    """
    lone = {n.id for n in problem.nets if n.cut and len(n.pins) == 1}
    out: list[Ref] = []
    laned: set[PinRef] = set()
    for fan in (f for f in flow.fans if lone & set(f.nets)):
        pins = [a.pin for a in (*fan.drivers, *fan.legs)]
        laned |= set(pins)
        for page in dict.fromkeys(where[a.column or a.pin.sym] for a in (*fan.drivers, *fan.legs)):
            pin = _page_pin(fan, page, where)
            out.append(Ref(fan.nets[0], RefKind.STUB, (RefEnd(page, None, pin),)))
    return out, laned


def stubs(
    problem: PlacementProblem, flow: FlowGraph, where: Mapping[str, int], cuts: Sequence[Ref]
) -> list[Ref]:
    """A crossing net ends in a stub at each boundary pin of it and some page-alone ends.

    `net.cut` pins stub once per line (`_first_of_lines`). An end with an arrow, tag, copy or
    anchor gets none (layout-0338).
    """
    marked = {e.pin for r in cuts if r.kind is not RefKind.STUB for e in r.ends if e.pin}
    boundary = {p for u in problem.facts.units for p in u.boundary}
    unit_of = {s.id: s.unit for s in problem.symbols}
    lined = {c.pin for n in problem.nets for c in n.cut if c.line}  # a line stubs once, not a pin
    out: list[Ref] = []
    crossed: set[PinRef] = set()
    for net in sorted((n for n in problem.nets if n.crosses_unit), key=lambda n: natural_key(n.id)):
        drawn = [p for p in net.pins if p.sym in where]
        crossing = _crossing(drawn, where, boundary, unit_of)
        ends = tuple(RefEnd(where[p.sym], None, p) for p in drawn if p in crossing - marked - lined)
        crossed |= crossing - lined
        if ends:
            out.append(Ref(net.id, RefKind.STUB, ends))
    anchored = {a.pin for a in problem.anchors}  # a power symbol on the pin ends its net
    fanned, laned = fan_stubs(problem, flow, where)
    return out + fanned + _first_of_lines(problem, where, marked | crossed | anchored | laned)
