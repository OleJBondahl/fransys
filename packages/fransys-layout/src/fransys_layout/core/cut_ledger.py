"""Stage 4: one carrier per required conductor, decided at the cut (CUT-LEDGER CL1).

A conductor is INK when both its pins stand on one page and no cut severs the pair (R1008); the router draws it.
Every other conductor is REF: the ink component of its near pin holds one reference end, or is covered by an arrow, tag,
copy or anchor (a harness line covers nothing, R1157). A component apart from its group is joined by a loop pair or ended by a stub (A21).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from itertools import permutations
from typing import TYPE_CHECKING, NamedTuple

from .cut_bundle import bundled, leg_stubs
from .cut_drawn import stand_pins
from .cut_pieces import hole_pin, join, joined, key, pairs, split, trunked
from .keys import natural_key
from .net_keys import is_lone_cut
from .values import PinRef, Ref, RefEnd, RefKind, StandClass

if TYPE_CHECKING:
    from collections.abc import Collection, Hashable, Mapping, Sequence
    from collections.abc import Set as AbstractSet

    from .flow_values import Fan, FlowGraph
    from .unionfind import UnionFind
    from .values import PagePlan, PlacementProblem

__all__ = ("Account", "account", "copies")

type Pair = tuple[PinRef, PinRef]
_PAIR = 2


@dataclass(frozen=True, slots=True)
class Account:
    """The cut's one account: the `(near, far)` pairs drawn as a wire on their page, and the stubs that carry the rest."""

    ink: frozenset[Pair]
    refs: tuple[Ref, ...]
    stubbed: frozenset[PinRef] = frozenset()
    leads: frozenset[PinRef] = frozenset()  # no field holds lead membership: `stubbed` lacks the held lead pins and holds crossing pins (R1577)
    unjoined: tuple[
        tuple[str, Pair], ...
    ] = ()  # (net, (near, far)): pieces the loop must join, stood by `widen._stand` through the route fallback, no reserve and no re-cut (R1713)


def _ink(far_ends: Collection[Pair], where: Mapping[str, int], severed: Collection[Pair]) -> frozenset[Pair]:
    """The drawn `(P, F)` pairs: its symbols share a page and the cut does not sever it (R1008): a cut-end pin keeps its neighbour."""
    return frozenset(
        (near, far)
        for near, far in far_ends
        if (near, far) not in severed and (page := where.get(near.sym)) is not None and page == where.get(far.sym)
    )


def _severed(far_ends: Collection[Pair], planned: Sequence[Ref]) -> set[Pair]:
    """The pairs the cut severs: those between a reference's own ends, and every pair at the lone end of an arrow (CUT-COPY-ENDS).

    A copy stands at one end of its conductor and the wire at its page is drawn; an arrow with no other end here cuts the wire.
    """
    pins = [(r.kind, [e.pin for e in r.ends if e.pin]) for r in planned]
    lone = {p for kind, ends in pins if kind is RefKind.ARROW and len(set(ends)) == 1 for p in ends}
    return {pair for _, ends in pins for pair in permutations(ends, 2)} | {(a, b) for a, b in far_ends if a in lone or b in lone}


def _joins(flow: FlowGraph) -> list[frozenset[PinRef]]:
    """The pins one column's join wire ties to its fan end, per net: a folded member's join (layout-0482)."""
    found: list[frozenset[PinRef]] = []
    for side in (s for col in flow.columns for s in (col.heads, col.feet)):
        ends = [e for e in side if e.pin and e.kind in {"join", "fan"}]
        found += [frozenset(e.pin for e in ends if e.net == net and e.pin) for net in dict.fromkeys(e.net for e in ends)]
    return found


def _covered(problem: PlacementProblem, refs: Sequence[Ref], held: tuple[AbstractSet[PinRef], Sequence[AbstractSet[PinRef]]]) -> set[PinRef]:
    """The pins a reference stands at or for: an end or an anchor, a fan lane's pins, and the pins a join wire ties to one of them.

    A harness line covers none (R1157).
    """
    laned, joins = held
    covered = {e.pin for r in refs for e in r.ends if e.pin} | {a.pin for a in problem.anchors} | laned
    return covered.union(*(j for j in joins if not covered.isdisjoint(j)))


def stand_class(attachments: int, *, leg: bool = False) -> StandClass:
    """LEG: a one-sided pin on a fan; TRUNK_END: an attachment of a fan with two or more on its page; PIN: every other end (CL2)."""
    if leg:
        return StandClass.LEG
    return StandClass.TRUNK_END if attachments >= _PAIR else StandClass.PIN


def copy_nets(fan: Fan, copyable: AbstractSet[str]) -> tuple[str, ...]:
    """The nets a copyable fan's copies carry (G5): one per net, a bundle's one for all; none for a fan not copyable."""
    if fan.id not in copyable:
        return ()
    return fan.nets[:1] if fan.lanes > 1 else fan.nets


def _page_pin(fan: Fan, page: int, where: Mapping[str, int], net: str | None = None) -> PinRef | None:
    """The fan's first pin (of `net` when given), in the order of its ids, that stands on `page`."""
    on = [a.pin for a in (*fan.drivers, *fan.legs) if where.get(a.column or a.pin.sym) == page and net in (None, a.net)]
    return min(on, key=lambda p: (natural_key(p.sym), natural_key(p.pin))) if on else None


def _copy_stand(fan: Fan, page: int, where: Mapping[str, int]) -> StandClass:
    """A copy on a page where the fan has one attachment stands at its trunk end, where that attachment's drop ends; else at its pin."""
    on = sum(where.get(a.column or a.pin.sym) == page for a in (*fan.drivers, *fan.legs))
    return StandClass.TRUNK_END if on == 1 else StandClass.PIN


def copies(flow: FlowGraph, where: Mapping[str, int], copyable: AbstractSet[str]) -> list[Ref]:
    """The one function that plans copies: each net of a copyable fan on two or more pages, an end on each page beyond the hub's.

    A copy covers one conductor (R1133, R866): an end names the net's first pin on its page; the cost reads `copy_nets`.
    """
    out: list[Ref] = []
    for fan in flow.fans:
        attached = (*fan.drivers, *fan.legs)
        pages = {where[n] for a in attached if (n := a.column or a.pin.sym) in where}
        if len(pages) > 1 and (nets := copy_nets(fan, copyable)):
            hub = next(a.column for a in attached if a.pin.sym == fan.hub)
            for net in nets:
                ends = tuple(
                    RefEnd(p, hub, _page_pin(fan, p, where, net if fan.lanes == 1 else None), stand=_copy_stand(fan, p, where))
                    for p in sorted(pages - {where[hub or ""]})
                )
                out.append(Ref(net, RefKind.COPY, ends))
    return out


def _attached_on(fan: Fan, where: Mapping[str, int]) -> Counter[int]:
    """The fan's attachments on each page it stands on: the count `stand_class` takes (CL2)."""
    return Counter(where[n] for a in (*fan.drivers, *fan.legs) if (n := a.column or a.pin.sym) in where)


def _fan_refs(problem: PlacementProblem, flow: FlowGraph, where: Mapping[str, int]) -> tuple[list[Ref], set[PinRef]]:
    """One stub per page of each fan whose net is a lone cut net (R499), listing the page's pins it ends, and the pins it lanes."""
    lone = {n.id for n in problem.nets if is_lone_cut(is_cut=bool(n.cut), pin_count=len(n.pins))}
    refs: list[Ref] = []
    laned: set[PinRef] = set()
    for fan in (f for f in flow.fans if lone & set(f.nets)):
        attached = (*fan.drivers, *fan.legs)
        laned |= {a.pin for a in attached}
        pages = _attached_on(fan, where)
        refs += [
            Ref(
                fan.nets[0],
                RefKind.STUB,
                (
                    bundled(
                        RefEnd(p, None, _page_pin(fan, p, where), stand=stand_class(pages[p])),
                        [a.pin for a in attached if where[a.column or a.pin.sym] == p],
                    ),
                ),
            )
            for p in pages
        ]
    return refs, laned


def _net_of(problem: PlacementProblem) -> dict[PinRef, str]:
    """The net of each pin; a pin of a required group with none (a terminal's other side) takes its symbol's."""
    net_of = {p: n.id for n in problem.nets for p in n.pins}
    by_sym = {p.sym: n for p, n in net_of.items()}
    return net_of | {p: by_sym[p.sym] for g in problem.facts.groups for p in g if p not in net_of and p.sym in by_sym}


def _crossing(problem: PlacementProblem, flow: FlowGraph, where: Mapping[str, int], held: AbstractSet[PinRef]) -> list[Ref]:
    """One stub per crossing net at its boundary pins, its page-alone ends in units without one and every pin wired out of the set, not in `held`.

    A pin wired to a far pin that stands in no page of this set has an undrawn conductor whatever its page holds (layout-0338, S4).
    """
    wired_out = {a for a, b in problem.facts.far_ends if b.sym not in where}
    boundary = {p for u in problem.facts.units for p in u.boundary}
    unit_of = {s.id: s.unit for s in problem.symbols}
    on = {a.pin: _attached_on(f, where) for f in flow.fans for a in (*f.drivers, *f.legs)}
    out: list[Ref] = []
    for net in (n for n in problem.nets if n.crosses_unit):
        placed = [p for p in net.pins if p.sym in where]
        pages = [where[p.sym] for p in placed]
        in_units = {unit_of[p.sym] for p in placed if p in boundary}
        ends = tuple(
            RefEnd(where[p.sym], None, p, stand=stand_class(on[p][where[p.sym]] if p in on else 0))
            for p in placed
            if p not in held and (p in boundary or p in wired_out or (pages.count(where[p.sym]) == 1 and unit_of[p.sym] not in in_units))
        )
        if ends:
            out.append(Ref(net.id, RefKind.STUB, ends))
    return out


def _leads(problem: PlacementProblem, flow: FlowGraph, where: Mapping[str, int]) -> dict[PinRef, None]:
    """The cut pins no wire on their own page joins: no other pin of their net stands there (R481), in net order.

    A fan lane or an open end has its own wire. `where` maps a symbol to its page; a symbol it does not name is on no page.
    """
    wired = {a.pin for f in flow.fans for a in (*f.drivers, *f.legs)} | {e.pin for c in flow.columns for e in (*c.heads, *c.feet) if e.kind == "open"}
    out: dict[PinRef, None] = {}
    for net in problem.nets:
        for pin in (p for p in net.pins if p.sym in where and p not in wired):
            pages = {where.get(q.sym) for q in net.pins if q != pin}
            if where[pin.sym] not in pages and (net.cut or pages):
                out[pin] = None
    return out


def _lead_stubs(leads: Collection[PinRef], where: Mapping[str, int], net_of: Mapping[PinRef, str], held: AbstractSet[PinRef]) -> list[Ref]:
    """One stub at each lead pin not in `held`."""
    return [Ref(net_of[p], RefKind.STUB, (RefEnd(where[p.sym], None, p),)) for p in leads if p not in held]


class _Held(NamedTuple):
    """What the cut holds while it mends a group: the problem, each symbol's page and piece, each pin's net, a fan lane's pins, the join wires."""

    problem: PlacementProblem
    where: Mapping[str, int]
    piece: Mapping[str, Hashable]
    net_of: Mapping[PinRef, str]
    laned: AbstractSet[PinRef]
    joins: Sequence[AbstractSet[PinRef]]
    conductors: AbstractSet[Pair]

    def covered(self, refs: Sequence[Ref]) -> set[PinRef]:
        return _covered(self.problem, refs, (self.laned, self.joins))


def _apart(parts: Sequence[list[PinRef]], ended: AbstractSet[PinRef], touched: AbstractSet[PinRef]) -> tuple[list[PinRef], list[PinRef]] | None:
    """The first piece no stub ends, a piece a reference touches before one none does (so the pin order of a group decides nothing), and the rest."""
    left = [p for p in parts if ended.isdisjoint(p)]
    first = next((p for p in left if not touched.isdisjoint(p)), next(iter(left), None))
    return None if first is None else (first, [q for p in parts if p is not first for q in p])


def _mend(group: Sequence[PinRef], held: _Held, refs: tuple[Sequence[Ref], list[Ref]], wired: UnionFind) -> list[tuple[str, Pair]]:
    """The stubs and join pairs of one required group: a piece no reference touches is ended by a stub, a piece one touches is joined by a pair.

    A join stands in the routing loop as a fallback tag pair, never as a reserved stub: a stub moved the cut pass over pass (R1711).
    """
    planned, made = refs
    far_ends = held.problem.facts.far_ends
    ended = held.covered([r for r in (*planned, *made) if r.kind in {RefKind.STUB, RefKind.COPY} or len(r.ends) < _PAIR])
    touched = held.covered([*planned, *made])
    unjoined: list[tuple[str, Pair]] = []
    while apart := _apart(split(group, held.piece, wired, held.conductors), ended, touched):
        part, rest = apart
        if touched.isdisjoint(part) or not rest:
            pin = hole_pin(part, far_ends, held.net_of)
            made.append(Ref(held.net_of[pin], RefKind.STUB, (RefEnd(held.where[pin.sym], None, pin),)))
            ended.add(pin)
        else:
            unjoined.append(join(part, rest, far_ends, held.net_of))
            wired.union(key(unjoined[-1][1][0]), key(unjoined[-1][1][1]))
    return unjoined


def _made(
    problem: PlacementProblem,
    where: Mapping[str, int],
    ink: Collection[Pair],
    held: tuple[Sequence[Ref], set[PinRef], Mapping[str, Hashable]],
    leads: tuple[Collection[PinRef], FlowGraph],
) -> tuple[list[Ref], list[tuple[str, Pair]]]:
    """The stubs the cut adds and the pairs the loop joins (layout-0508 A21).

    `held` is the references planned, the pins a fan lane covers and each symbol's piece (its row); `_mend` stubs or joins its pieces.
    """
    planned, laned, piece = held
    joins = _joins(leads[1])
    far_ends = problem.facts.far_ends
    net_of = _net_of(problem)
    covered = _covered(problem, planned, (laned, joins))
    made = _crossing(problem, leads[1], where, covered | _drawn(far_ends, ink))
    made += _lead_stubs(leads[0], where, net_of, covered | {e.pin for r in made for e in r.ends if e.pin})
    wired = joined([*ink, *pairs(planned), *trunked(leads[1], where, net_of), *(pair for j in joins for pair in permutations(j, 2))])
    seen = _Held(problem, where, piece, net_of, laned, joins, set(far_ends))
    return made, [pair for group in problem.facts.groups for pair in _mend(group, seen, (planned, made), wired)]


def account(problem: PlacementProblem, flow: FlowGraph, where: Mapping[str, int], planned: Sequence[Ref], pages: Sequence[PagePlan]) -> Account:
    """The ink of the cut, a stub at each lead pin no reference stands at, and one at a pin of each drawn piece no reference carries.

    `planned`: the arrows, tags and copies the cut made. A piece's stub stands at its first pin wired to a pin outside it.
    """
    far_ends = problem.facts.far_ends
    ink = _ink(far_ends, where, _severed(far_ends, planned))
    fanned, laned = _fan_refs(problem, flow, where)
    cells = {c.id: [cell.sym for lane in c.lanes for cell in lane.cells] for c in flow.columns}
    piece = {s: (plan.page, r) for plan in pages for r, row in enumerate(plan.rows) for col in row.columns for s in (col, *cells.get(col, ()))}
    lead = _leads(problem, flow, where)
    made, unjoined = _made(problem, where, ink, (planned, laned, {s: piece.get(s, (p, None)) for s, p in where.items()}), (lead, flow))
    kept, legs = _legs(problem, flow, where, pages, (ink, made))
    refs = _named([*_merged([*kept, *fanned]), *legs], far_ends, ink)
    return Account(ink, tuple(refs), frozenset(e.pin for r in made for e in r.ends if e.pin), frozenset(lead), tuple(unjoined))


def _named(refs: Sequence[Ref], far_ends: Collection[Pair], ink: Collection[Pair]) -> list[Ref]:
    """Each stub end names the far pin of every undrawn conductor at its pin (and at the pins it also stands for): one box, a line each (R1581)."""
    undrawn: dict[PinRef, list[PinRef]] = {}
    for near, far in far_ends:
        if (near, far) not in ink:
            undrawn.setdefault(near, []).append(far)
    return [replace(r, ends=tuple(_with_far(e, undrawn) for e in r.ends)) if r.kind is RefKind.STUB else r for r in refs]


def _with_far(end: RefEnd, undrawn: Mapping[PinRef, Sequence[PinRef]]) -> RefEnd:
    """`end` with the undrawn far pins of its pin, then of each pin it also stands for."""
    pins = (end.pin, *end.also)
    return replace(end, far=tuple(dict.fromkeys(far for pin in pins for far in undrawn.get(pin, ()))))


def _drawn(far_ends: Collection[Pair], ink: Collection[Pair]) -> set[PinRef]:
    """The pins whose every conductor is drawn: they carry no marker, and a stub at one would name no conductor that leaves."""
    return {a for a, _ in far_ends} - {a for a, b in far_ends if (a, b) not in ink}


def _far_pages(far_ends: Collection[Pair], ink: Collection[Pair], where: Mapping[str, int]) -> dict[PinRef, set[tuple[int, str]]]:
    """Per pin the (page, symbol) of each far end whose conductor is not drawn; a far end in no page of this set is page 0."""
    far: dict[PinRef, set[tuple[int, str]]] = {}
    for a, b in far_ends:
        if (a, b) not in ink:
            far.setdefault(a, set()).add((where.get(b.sym, 0), b.sym))
    return far


def _legs(
    problem: PlacementProblem, flow: FlowGraph, where: Mapping[str, int], pages: Sequence[PagePlan], wired: tuple[Collection[Pair], Sequence[Ref]]
) -> tuple[list[Ref], list[Ref]]:
    """`wired` is the ink and the stubs `made`, split into the stubs that stand as they are and the LEG stubs of one-sided fan pins (ONE-SIDED-PIN).

    A leg stands at the trunk end of its pin's lane, with that row. The pins of a fan whose undrawn conductors all go to one
    far page and device are a bundle: one leg per page covers them (CL1 covered rule, R866; `cut_bundle`).
    """
    ink, made = wired
    sided = {
        p
        for p, at in stand_pins(problem.facts.far_ends, (ink, flow.fans, {e.pin for r in made for e in r.ends if e.pin}), problem.symbols).items()
        if not any(at.values())
    }
    rows = {(plan.page, c): r for plan in pages for r, row in enumerate(plan.rows) for c in row.columns}
    far = _far_pages(problem.facts.far_ends, ink, where)
    undrawn = {a for a, b in problem.facts.far_ends if (a, b) not in ink}
    legged = sided & undrawn  # MARKER-FREE-SIDE (R1308, R1541): a leg stands only at a pin with an undrawn conductor
    net_of = {p: n.id for n in problem.nets for p in n.pins}
    legs: list[Ref] = []
    carried: set[PinRef | None] = set()
    for fan in flow.fans:
        by_page: dict[int, list[RefEnd]] = {}
        for a in (*fan.drivers, *fan.legs):
            if a.pin in legged and a.column is not None and a.column in where and (where[a.column], a.column) in rows:
                by_page.setdefault(where[a.column], []).append(
                    RefEnd(where[a.column], a.column, a.pin, rows[where[a.column], a.column], stand_class(0, leg=True))
                )
        for ends in by_page.values():
            legs += leg_stubs(ends, far, net_of)
            carried |= {e.pin for e in ends}
    return [replace(r, ends=k) for r in made if (k := tuple(e for e in r.ends if e.pin not in carried and e.pin in undrawn))], legs


def _merged(kept: Sequence[Ref]) -> list[Ref]:
    """One stub a net: the PIN ends of a net's stubs stand in one reference (R804)."""
    by: dict[str, list[Ref]] = {}
    for r in kept:
        by.setdefault(r.net, []).append(r)
    return [
        Ref(n, RefKind.STUB, tuple(e for r in rs for e in r.ends))
        if len(rs) > 1 and all(e.stand is StandClass.PIN for r in rs for e in r.ends)
        else rs[0]
        for n, rs in by.items()
    ]
