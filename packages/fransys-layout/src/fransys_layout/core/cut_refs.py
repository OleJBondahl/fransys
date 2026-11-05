"""Stage 4, after the DP: the references the cut plans, and the findings it reports.

Arrows and tags per cut, a tag for each column spilled off a card, the P3 check (HEAD_OFF_LEGS) and a stub at each unit boundary pin
and each page-alone end.
`Fan.crossed` is neither read nor filled (layout-0275).
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from .cut_costs import is_pair, ref_name
from .cut_ends import (
    Lanes,
    lane_ends,
    link_over_empty_rows,
    link_over_pinless,
    row_starts,
    rows_of,
)
from .errors import CoreError
from .fan_head import fan_head, head_short
from .keys import natural_key
from .topology_elements import is_free_sided
from .values import Finding, PinRef, Ref, RefEnd, RefKind

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Mapping, Sequence

    from .cut_dp import Cut, Plan
    from .flow_values import BlockList, Column, FlowGraph
    from .values import Net, PlacementProblem


def copyable_fans(flow: FlowGraph, problem: PlacementProblem) -> frozenset[str]:
    """Fans whose hub is a free-sided symbol: it may be drawn again on each page the fan reaches.

    A hub whose n and s pins are both unit boundary pins is not: its copy joins nothing for a
    reader, so the cut plans an arrow pair (PAGE-CUT, R455).
    """
    syms = {s.id: s for s in problem.symbols}
    boundary = {p for u in problem.facts.units for p in u.boundary}
    return frozenset(
        f.id for f in flow.fans if f.hub is not None and is_free_sided(syms[f.hub]) and not {PinRef(f.hub, "n"), PinRef(f.hub, "s")} <= boundary
    )


def cut_sets(plan: Plan) -> tuple[set[int], set[int]]:
    """The page cuts, and the cuts that only start a row: the one test of which kind a cut is."""
    return (page := {k for _, k, _ in plan[:-1]}), {s - 1 for _, _, state in plan for s in row_starts(state)} - page


def references(
    cut: Cut,
    plan: Plan,
    page_of: Mapping[int, int],
    copyable: frozenset[str],
    pins: Mapping[str, Lanes],
) -> list[Ref]:
    """One arrow pair per trunk per cut it crosses, one tag pair per page-cut two-pin net.

    A page cut through a trunk with a free-sided hub plans no arrow: the hub is copied instead.
    Each end carries its row and the pin of the reference nearest it on its page (cut_ends).
    """
    row_of = rows_of(plan)
    page_cuts, row_only = cut_sets(plan)
    out: list[Ref] = []
    for b in sorted(row_only | page_cuts):
        for kind, names in ((RefKind.ARROW, cut.bounds[b].fans), (RefKind.TAG, cut.bounds[b].nets)):
            for name in names:
                if kind is RefKind.ARROW and b in page_cuts and name in copyable:
                    continue
                if kind is RefKind.TAG and b not in page_cuts:
                    continue  # rows.toml:98 one page one wire: a row cut keeps its wire, no tag
                at = tuple((q, cut.seq[q].column) for q in (b, b + 1))
                if ends := lane_ends(name, pins[name], at, page_of, row_of):
                    out.append(Ref(name, kind, ends, b))
    rows = {n: frozenset((page_of[i], row_of[i]) for p in lanes for i, _ in p) for n, lanes in pins.items()}
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
        raise CoreError(msg)
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


def across(flow: FlowGraph, where: Mapping[str, int], planned: Collection[Ref], nets: Iterable[Net] = ()) -> list[Ref]:
    """A tag pair for each across-body link (layout-0440) and each handed link the cut left on one page (`Net.tagged`, layout-0508).

    The cut plans the handed link's pair, so placement reserves its room; a link the cut already planned as references keeps those.
    """
    done = {(r.net, e.pin) for r in planned for e in r.ends}
    handed = {(n.id, frozenset(t)) for n in nets for t in n.tagged}
    return [
        Ref(link.net, RefKind.TAG, tuple(RefEnd(where[a.column or a.pin.sym], a.column, a.pin) for a in link.ends))
        for link in flow.cross_links
        if (link.tagged or (link.net, frozenset(a.pin for a in link.ends)) in handed) and not all((link.net, a.pin) in done for a in link.ends)
    ]


def tag_links(flow: FlowGraph, tags: Collection[Ref]) -> FlowGraph:
    """`flow` with each link `across` planned as a tag pair flagged `tagged`: a planned pair is never routed, its markers join its ends.

    A handed link is one or the other: planned at every end by the cut and routed where its ends share a page, or a tag pair (R1727).
    """
    keys = {(r.net, frozenset(e.pin for e in r.ends)) for r in tags}
    links = tuple(replace(ln, tagged=True) if (ln.net, frozenset(a.pin for a in ln.ends)) in keys else ln for ln in flow.cross_links)
    return flow if links == flow.cross_links else replace(flow, cross_links=links)


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


def row_tags(cut: Cut, plan: Plan, flow: FlowGraph) -> frozenset[str]:
    """The fans of a two-pin net that a cut tags, a row cut or a page cut: routing wraps their wire, they get no trunk (DANGLING-0223)."""
    page_cuts, row_only = cut_sets(plan)
    wrapped = {n for b in row_only | page_cuts for n in cut.bounds[b].nets}
    return frozenset(f.id for f in flow.fans if is_pair(f) and ref_name(f) in wrapped)
