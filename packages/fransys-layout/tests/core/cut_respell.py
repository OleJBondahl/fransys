"""Respell every id of a stage 4 input by natural-key rank, and map a cut result back.

The cases use symbols, nets, groups, columns, fans and blocks only (no facts, no pair hints),
so those are the ids spelled here. A split column's `#a` and `#b` follow its column id.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Any

from fransys_layout.core import natural_key

if TYPE_CHECKING:
    from collections.abc import Callable

    from fransys_layout.core import (
        Attach,
        Block,
        BlockList,
        CutResult,
        End,
        FlowGraph,
        PagePlacement,
        PinRef,
        Placement,
        PlacementProblem,
    )

Maps = dict[str, str]
Canon = tuple[tuple[Any, ...], tuple[Any, ...], tuple[Any, ...]]


def spelling(ids: set[str], form: str) -> Maps:
    """Each id to the form spelled with its natural-key rank."""
    return {i: form.format(n) for n, i in enumerate(sorted(ids, key=natural_key), 1)}


def id_sets(
    prob: PlacementProblem, flow: FlowGraph, lists: tuple[BlockList, ...]
) -> dict[str, set[str]]:
    """The ids of the input, by kind."""
    return {
        "sym": {s.id for s in prob.symbols},
        "net": {n.id for n in prob.nets},
        "group": {s.group for s in prob.symbols if s.group}
        | {g for h in (prob.hints.group_order,) for g in h},
        "col": {c.id for c in flow.columns},
        "fan": {f.id for f in flow.fans},
        "block": {b.id for bl in lists for b in bl.blocks},
    }


def make_maps(sets: dict[str, set[str]], form: str) -> Maps:
    """One map over every id kind; kinds never share an id."""
    out: Maps = {}
    for kind, ids in sets.items():
        out.update(spelling(ids, f"{kind[0].upper()}{form}"))
    return out


def _pin(p: PinRef, m: Maps) -> PinRef:
    return replace(p, sym=m[p.sym])


def _end(e: End, m: Maps) -> End:
    return replace(
        e,
        net=m.get(e.net or "", e.net),
        pin=_pin(e.pin, m) if e.pin else None,
        fan=m[e.fan] if e.fan else None,
    )


def _attach(a: Attach, m: Maps) -> Attach:
    return replace(a, column=m[a.column] if a.column else None, pin=_pin(a.pin, m))


def respell_problem(prob: PlacementProblem, m: Maps) -> PlacementProblem:
    syms = tuple(
        replace(s, id=m[s.id], group=m[s.group] if s.group else None) for s in prob.symbols
    )
    nets = tuple(replace(n, id=m[n.id], pins=tuple(_pin(p, m) for p in n.pins)) for n in prob.nets)
    hints = replace(
        prob.hints,
        group_order=tuple(m[g] for g in prob.hints.group_order),
        break_before=frozenset(m[g] for g in prob.hints.break_before),
    )
    return replace(prob, symbols=syms, nets=nets, hints=hints)


def respell_flow(flow: FlowGraph, m: Maps) -> FlowGraph:
    cols = tuple(
        replace(
            c,
            id=m[c.id],
            lanes=tuple(
                replace(ln, cells=tuple(replace(x, sym=m[x.sym]) for x in ln.cells))
                for ln in c.lanes
            ),
            heads=tuple(_end(e, m) for e in c.heads),
            feet=tuple(_end(e, m) for e in c.feet),
        )
        for c in flow.columns
    )
    fans = tuple(
        replace(
            f,
            id=m[f.id],
            nets=tuple(m[n] for n in f.nets),
            drivers=tuple(_attach(a, m) for a in f.drivers),
            legs=tuple(_attach(a, m) for a in f.legs),
            hub=m[f.hub] if f.hub else None,
            crossed=tuple((m[sym], perm) for sym, perm in f.crossed),
        )
        for f in flow.fans
    )
    links = tuple(
        replace(x, net=m[x.net], ends=tuple(_attach(a, m) for a in x.ends))
        for x in flow.cross_links
    )
    stands = tuple(replace(s, sym=m[s.sym]) for s in flow.stands)
    return replace(
        flow,
        columns=cols,
        fans=fans,
        cross_links=links,
        stands=stands,
        drawn=tuple(m[d] for d in flow.drawn),
    )


def respell_blocks(lists: tuple[BlockList, ...], m: Maps) -> tuple[BlockList, ...]:
    def block(b: Block) -> Block:
        return replace(
            b,
            id=m[b.id],
            columns=tuple(m[c] for c in b.columns),
            anchor=m[b.anchor] if b.anchor else None,
            fan=m[b.fan] if b.fan else None,
            group=m[b.group] if b.group else None,
        )

    return tuple(replace(bl, blocks=tuple(block(b) for b in bl.blocks)) for bl in lists)


def back_of(m: Maps) -> Callable[[str | None], str | None]:
    """The inverse map; a `#a` or `#b` split id maps by its column id."""
    inv = {new: old for old, new in m.items()}

    def back(i: str | None) -> str | None:
        if i is None or i in inv:
            return inv.get(i or "")
        return inv[i[:-2]] + i[-2:] if i[:-2] in inv else i

    return back


def canon(result: CutResult, back: Callable[[str | None], str | None]) -> Canon:
    """The result as plain tuples with every id mapped back; findings without their text."""
    pages = tuple(
        (
            p.page,
            tuple(
                (tuple(map(back, r.columns)), tuple(map(back, r.blocks)), r.height_est)
                for r in p.rows
            ),
            p.forced_end,
            tuple(map(back, p.groups)),
        )
        for p in result.spec.pages
    )
    refs = tuple(
        (
            back(r.net),
            r.kind,
            tuple((e.page, back(e.column), e.pin and (back(e.pin.sym), e.pin.pin)) for e in r.ends),
        )
        for r in result.spec.reference_plan
    )
    finds = tuple((f.code, f.page, back(f.subject)) for f in result.spec.findings)
    return pages, refs, finds


def _any(i: str | None, m: Maps) -> str | None:
    """An id spelled by the map; a `#a` or `#b` split id by its column id; others unchanged."""
    if i is None or i in m:
        return m.get(i or "")
    return m[i[:-2]] + i[-2:] if i[:-2] in m else i


def respell_cut(cut: CutResult, m: Maps) -> CutResult:
    """The stage 4 result with every id spelled by the map (flow and blocks as the stage 4 ones)."""
    pages = tuple(
        replace(
            p,
            rows=tuple(
                replace(
                    r,
                    columns=tuple(_any(c, m) for c in r.columns),
                    blocks=tuple(_any(b, m) for b in r.blocks),
                )
                for r in p.rows
            ),
            groups=tuple(_any(g, m) for g in p.groups),
        )
        for p in cut.spec.pages
    )
    refs = tuple(
        replace(
            r,
            net=_any(r.net, m),
            ends=tuple(
                replace(e, column=_any(e.column, m), pin=_pin(e.pin, m) if e.pin else None)
                for e in r.ends
            ),
        )
        for r in cut.spec.reference_plan
    )
    finds = tuple(replace(f, subject=_any(f.subject, m)) for f in cut.spec.findings)
    spec = replace(cut.spec, pages=pages, reference_plan=refs, findings=finds)
    flow, blocks = respell_flow(cut.flow, m), respell_blocks(cut.blocks, m)
    return replace(cut, spec=spec, flow=flow, blocks=blocks)


def _page(p: PagePlacement, back: Callable[[str | None], str | None]) -> tuple[Any, ...]:
    placed = sorted(p.placed, key=lambda q: natural_key(back(q.sym) or ""))
    syms = tuple(
        (back(q.sym), q.orient, q.body, q.footprint, tuple((x.pin, x.x, x.y) for x in q.pin_xy))
        for q in placed
    )
    gaps = sorted(
        ((back(g.left), back(g.right), g.x0, g.x1, g.tracks, g.y0, g.y1) for g in p.gaps), key=repr
    )
    trunks = sorted(((back(t.fan), t.y, t.x0, t.x1, t.lanes) for t in p.trunks), key=repr)
    return p.page, syms, tuple(gaps), tuple(trunks), p.rows


def canon_placement(pl: Placement, back: Callable[[str | None], str | None]) -> tuple[Any, ...]:
    """The placement as plain tuples with every id mapped back; no gap id, no finding text."""
    finds = tuple((f.code, f.page, back(f.subject)) for f in pl.findings)
    return tuple(_page(p, back) for p in pl.pages), finds
