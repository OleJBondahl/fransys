"""The `solve` invariants IS.1 to IS.7 (layout-0296): each returns its messages, [] when it holds.

IS.8 and IS.9 stay in `test_invariants.py`. The checkers run `solve` themselves where the rule
compares two runs (IS.1, IS.7) and read a given `CoreLayout` otherwise.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import replace
from typing import TYPE_CHECKING, get_args

from cut_respell import back_of, canon_placement, id_sets, make_maps, respell_problem
from route_oracle import connected_or_referenced
from test_invariants import check_label_conflicts

from fransys_layout.core import build_flow, to_plain
from fransys_layout.core.blocks import assign_blocks
from fransys_layout.core.geometry import overlaps
from fransys_layout.core.solve import solve
from fransys_layout.core.values import FindingCode

if TYPE_CHECKING:
    from collections.abc import Callable

    from fransys_layout.core import Options, PinRef, PlacementProblem
    from fransys_layout.core.outputs import CoreLayout
    from fransys_layout.core.values import BlockList


def _blocks(prob: PlacementProblem, options: Options) -> tuple[BlockList, ...]:
    """Stages 1 and 2 on a problem."""
    return assign_blocks(build_flow(prob, options), prob, options)


def check_pure(prob: PlacementProblem, options: Options) -> list[str]:
    """IS.1: two runs give one plain form, and reversing the symbols and nets changes nothing."""
    first = solve(prob, options)
    msgs = []
    if to_plain(first) != to_plain(solve(prob, options)):
        msgs.append("IS.1 solve twice gives two layouts")
    reversed_prob = replace(prob, symbols=prob.symbols[::-1], nets=prob.nets[::-1])
    if to_plain(solve(reversed_prob, options)) != to_plain(first):
        msgs.append("IS.1 reversing the symbols and nets changes the layout")
    return msgs


def check_placed_once(layout: CoreLayout, prob: PlacementProblem, options: Options) -> list[str]:
    """IS.2: every drawn symbol has one Placed, and no undrawn symbol has any."""
    drawn = set(build_flow(prob, options).drawn)
    got = Counter(p.sym for pg in layout.placement.pages for p in pg.placed)
    msgs = [f"IS.2 {s}: {got[s]} Placed, want 1" for s in sorted(drawn) if got[s] != 1]
    msgs += [f"IS.2 {s}: placed but not drawn" for s in sorted(set(got) - drawn)]
    return msgs


def check_every_net(layout: CoreLayout, prob: PlacementProblem) -> list[str]:
    """IS.3: I6.2 on every page with the fallback tags counted, and a marker at every ref end.

    An end that fits nowhere inside the page is a MARKER_UNPLACED on its symbol (R436), not a gap.
    """
    nodes = {s.id: s.nodes for s in prob.symbols}
    msgs = [
        f"IS.3 {n.id} on page {pg.page}: open and not referenced"
        for n in prob.nets
        for pg in layout.routes.pages
        if not connected_or_referenced(
            layout.routes, layout.placement, layout.references, n, pg.page, nodes
        )
    ]
    ends = Counter(
        (r.net, e.page, e.pin) for r in layout.references for e in r.ends if e.pin is not None
    )
    marks = Counter((m.net, m.page, m.end) for m in layout.annotations.markers)
    unplaced = _unplaced_ends(layout)
    msgs += [
        f"IS.3 {net} on page {page}: {marks[net, page, pin]} marker(s) at {pin}, want {n}"
        for (net, page, pin), n in sorted(ends.items(), key=repr)
        if marks[net, page, pin] != n and (page, pin.sym, net) not in unplaced
    ]
    return msgs


def _unplaced_ends(layout: CoreLayout) -> set[tuple[int | None, str, str]]:
    """The (page, symbol, net) of each MARKER_UNPLACED, read from its page and subject (R449.1)."""
    ends = set()
    for f in layout.findings:
        if f.code == "MARKER_UNPLACED" and f.subject:
            sym, net = f.subject.split(",")
            ends.add((f.page, sym, net))
    return ends


def check_no_overlap(layout: CoreLayout, prob: PlacementProblem, options: Options) -> list[str]:
    """IS.4: I5.2 (no two bodies, no body and table overlap on a page) and I8.2 on every page."""
    msgs = []
    notes = layout.annotations
    for pg in layout.placement.pages:
        boxes = [(p.sym, p.body) for p in pg.placed]
        boxes += [(f"table of {t.coil}", t.box) for t in notes.tables if t.page == pg.page]
        msgs += [
            f"IS.4 {a} and {b} on page {pg.page}: hard boxes overlap"
            for i, (a, ba) in enumerate(boxes)
            for b, bb in boxes[i + 1 :]
            if overlaps(ba, bb)
        ]
    return msgs + check_label_conflicts(
        layout.placement,
        layout.routes,
        notes.markers,
        notes.tables,
        notes.annexes,
        layout.findings,
        prob.area,
        options,
    )


def check_findings(layout: CoreLayout, prob: PlacementProblem, options: Options) -> list[str]:
    """IS.5: every code is in the vocabulary; a finding's page and subject exist."""
    codes, pages = set(get_args(FindingCode)), {p.page for p in layout.pages}
    flow = build_flow(prob, options)
    known = {s.id for s in prob.symbols} | {n.id for n in prob.nets}
    known |= {c.id for c in flow.columns} | {f.id for f in flow.fans}
    known |= {b.id for bl in _blocks(prob, options) for b in bl.blocks}
    msgs = []
    for f in layout.findings:
        if f.code not in codes:
            msgs.append(f"IS.5 {f.code}: not in the finding vocabulary")
        if f.page is not None and f.page not in pages:
            msgs.append(f"IS.5 {f.code}: page {f.page} does not exist")
        if f.subject and not all(t in known for t in f.subject.split(",")):
            msgs.append(f"IS.5 {f.code}: subject {f.subject!r} names nothing in the problem")
    return msgs


def check_plan_drawn(layout: CoreLayout) -> list[str]:
    """IS.6: the markers per class equal the reference plan's ends per class.

    An end named by a MARKER_UNPLACED (its text opens with the kind) counts as drawn (R436).
    """
    planned = Counter(r.kind for r in layout.references for _ in r.ends)
    drawn = Counter(m.kind for m in layout.annotations.markers)
    unplaced = _unplaced_ends(layout)
    drawn += Counter(
        r.kind
        for r in layout.references
        for e in r.ends
        if e.pin is not None and (e.page, e.pin.sym, r.net) in unplaced
    )
    return [
        f"IS.6 {kind}: {drawn[kind]} marker(s), {planned[kind]} planned end(s)"
        for kind in sorted(planned.keys() | drawn.keys(), key=str)
        if planned[kind] != drawn[kind]
    ]


def _canon(layout: CoreLayout, back: Callable[[str | None], str | None]) -> tuple:
    wires = tuple(
        (
            pr.page,
            tuple(sorted(((back(w.net), w.points, w.kind, w.lanes) for w in pr.wires), key=repr)),
        )
        for pr in layout.routes.pages
    )
    marks = tuple(
        sorted(
            (
                (back(m.net), m.kind, m.page, m.x, m.y, back(m.end.sym), m.end.pin)
                for m in layout.annotations.markers
            ),
            key=repr,
        )
    )
    finds = tuple((f.code, f.page, _back_ids(f.subject, back)) for f in layout.findings)
    return canon_placement(layout.placement, back), wires, marks, finds


def _back_ids(subject: str | None, back: Callable[[str | None], str | None]) -> str | None:
    """`back` of each id in a finding's subject, which may name several ("sym,net")."""
    return None if subject is None else ",".join(back(t) or t for t in subject.split(","))


def _parts(maps: dict[str, str]) -> Callable[[str | None], str | None]:
    """`back_of`, and the ids stage 3 spells from a symbol id ("c:S0001") by their parts."""
    inv = back_of(maps)

    def back(i: str | None) -> str | None:
        return None if i is None else ":".join(inv(part) or part for part in i.split(":"))

    return back


def _respelled(prob: PlacementProblem, maps: dict[str, str]) -> PlacementProblem:
    """`respell_problem`, and the symbol and group names of the facts, hints and annex owners."""

    def name(n: str) -> str:
        return maps.get(n, n)

    def pin(p: PinRef) -> PinRef:
        return replace(p, sym=name(p.sym))

    out = respell_problem(prob, maps)
    facts, hints = out.facts, out.hints
    facts = replace(
        facts,
        keep_whole=tuple(frozenset(map(name, k)) for k in facts.keep_whole),
        units=tuple(replace(u, boundary=tuple(map(pin, u.boundary))) for u in facts.units),
        mates=tuple((pin(a), pin(b)) for a, b in facts.mates),
    )
    hints = replace(
        hints,
        keep_together=tuple(frozenset(map(name, k)) for k in hints.keep_together),
        order_pairs=tuple((name(a), name(b)) for a, b in hints.order_pairs),
        chains=tuple(tuple(map(name, c)) for c in hints.chains),
        draw_in=tuple((name(a), name(b)) for a, b in hints.draw_in),
        sides=tuple((pin(p), side) for p, side in hints.sides),
    )
    annexes = tuple(replace(a, owner=name(a.owner)) for a in out.annexes)
    return replace(out, facts=facts, hints=hints, annexes=annexes)


def check_kind_blind(prob: PlacementProblem, options: Options, form: str = "{}") -> list[str]:
    """IS.7: respelling every symbol, net and group id changes the layout by the spelling only."""
    want = solve(prob, options)
    flow = build_flow(prob, options)
    maps = make_maps(id_sets(prob, flow, _blocks(prob, options)), form)
    got = solve(_respelled(prob, maps), options)
    if _canon(got, _parts(maps)) != _canon(want, _parts({})):
        return [f"IS.7 respelling the ids ({form}) changes the layout"]
    return []
