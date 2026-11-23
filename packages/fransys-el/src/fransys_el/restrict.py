"""The restriction of the whole problem to one drawing scope (R520 B1).

`restriction` cuts the whole problem down to one scope. A net cut by a scope keeps its in-set pins and ends in a stub.
"""

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from fransys_layout.core import CutEnd, Facts, Hints, PlacementProblem, leaves_of

from .placement_annexes import label_annexes, wider_annexes

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Mapping, Sequence

    from fransys_layout.core import Net, Options, PinRef, Size

    from .scopes import DrawingScope


__all__ = ["Restriction", "restriction"]

_MIN_ENDS = 2  # a wire needs two ends


def _carriers(
    pins: tuple[PinRef, ...],
    boundary: Collection[PinRef],
    bare: Collection[PinRef],
    outward: Collection[PinRef] = (),
) -> tuple[PinRef, ...]:
    """The one in-set pin that carries a cut net's continuation, or none when no conductor leaves.

    A pin in `bare` has no conductor out, so no far end to name. Of the rest a unit boundary pin
    comes first (it stubs anyway), then a pin mated to one outside the set; else the first (R468).
    """
    able = [p for p in pins if p not in bare]
    if not able:
        return ()
    held = [p for p in able if p in boundary] or [p for p in able if p in outward] or able
    return (held[0],)


def _joined(net: Net, own: int, scopes: Sequence[DrawingScope]) -> bool | None:
    """For a net `scopes[own]` shares a terminal of with other sets: whether all its ends lie in them.

    A terminal drawn in two sets joins them for a reader (R652): the net needs no stub between them.
    Each set stubs the ends it holds whose far end lies outside the sets joined to it (R950).
    """
    pins = {p.sym for p in net.pins}
    group = {own}
    grown = True
    while grown:
        grown = False
        for i, other in enumerate(scopes):
            if i not in group and any(scopes[j].symbols & other.symbols & pins for j in group):
                group.add(i)
                grown = True
    if len(group) < _MIN_ENDS or len({p.sym for p in net.pins if p.sym in scopes[own].symbols}) < _MIN_ENDS:
        return None
    return pins <= set().union(*(scopes[i].symbols for i in group))


def _net(
    net: Net,
    symbols: Collection[str],
    carry: tuple[Collection[PinRef], Collection[PinRef], Collection[PinRef]],
    ends: Collection[tuple[PinRef, PinRef]],
    pieces: Mapping[PinRef, str],
) -> tuple[Net, ...]:
    """`net` with the pins inside `symbols`: one `Net` per piece the set itself joins that has a carrier, none when no pin is inside.

    A cut piece names in `cut` the pin that continues outside. `pieces`: each pin's piece (`scopes.piece_names`); the first keeps the bundle.
    `carry` is the `_carriers` boundary, bare and outward pins; `ends` the far ends, to find a conductor between in-set pins.
    """
    pins = tuple(p for p in net.pins if p.sym in symbols)
    if len(pins) == len(net.pins) or not pins:
        return (net,) if pins else ()
    held: dict[str, list[PinRef]] = {}
    for pin in pins:
        held.setdefault(pieces.get(pin, net.id), []).append(pin)
    found: list[Net] = []
    for name, part in held.items():
        cut = _carriers(tuple(part), *carry)
        # one symbol's pins joined by no conductor need no wire between them: only the stub is drawn
        alone = len({p.sym for p in part}) == 1 and not any(a in part and b in part for a, b in ends)
        if cut:
            one = replace(net, pins=cut if alone else tuple(part), cut=tuple(CutEnd(p) for p in cut))
            found.append(one if len(held) == 1 else replace(one, id=name, bundle=None if found else net.bundle))
    return tuple(found)


def _whole(net: Net, scope: DrawingScope, boundary: Collection[PinRef]) -> Net:
    """`net` with the pins inside `scope` and no cut.

    A stub out of the unit stays at a boundary end that is the scope's own or printed in another document.
    """
    pins = tuple(p for p in net.pins if p.sym in scope.symbols)
    own_edge = any(p in boundary and (p.sym not in scope.away or p.sym in scope.abroad) for p in pins)
    return replace(net, pins=pins, cut=(), crosses_unit=net.crosses_unit and own_edge)


def _lined(net: Net, lines: Mapping[PinRef, str]) -> Net:
    """`net` with the line of each cut pin named."""
    return replace(net, cut=tuple(CutEnd(c.pin, lines.get(c.pin, "")) for c in net.cut))


def _outward(mates: Iterable[tuple[PinRef, PinRef]], symbols: Collection[str]) -> frozenset[PinRef]:
    """The pins in `symbols` whose mate half stands outside: a cut by the mate."""
    found = set()
    for pair in mates:
        for here, there in (pair, (pair[1], pair[0])):
            if _inside(here, symbols) and not _inside(there, symbols):
                found.add(here)
    return frozenset(found)


def _inside(pin: PinRef, symbols: Collection[str]) -> bool:
    return pin.sym in symbols


def _carried(facts: Facts, scope: DrawingScope, other: Collection[str], unit: Mapping[str, str]) -> Facts:
    """`facts` less the far ends in `other` (another unit's symbols) of a pin the container carries (model-0188).

    A pin is the container's when this scope owns its symbol (R1540): a copy of another unit's pin (away) shows only its face,
    and only its unit's inner wire (both ends in that unit) stays off this page (R1542).
    """
    owned = scope.symbols - scope.away | scope.abroad
    edge = {p for u in facts.units for p in u.boundary if p.sym in owned}
    theirs = {p for g in facts.groups for p in g if p.sym in scope.symbols and p not in edge}
    far = tuple((a, b) for a, b in facts.far_ends if not (b.sym in other and a.sym not in owned and unit[a.sym] == unit[b.sym]))
    groups = tuple(tuple(p for p in g if not (p.sym in other and theirs.intersection(g))) for g in facts.groups)
    return replace(facts, far_ends=far, groups=groups)


def _facts(facts: Facts, symbols: frozenset[str], bare: Collection[PinRef], gone: Collection[PinRef]) -> Facts:
    """The facts of one scope: each set cut to its symbols, each boundary and mate inside, each far end with its near pin inside.

    A boundary pin in `bare` has no conductor to name a stub's far end, so it is left out. A series
    region with a symbol outside is dropped: its neighbours share no net here.
    """
    units = tuple(replace(u, boundary=tuple(p for p in u.boundary if _inside(p, symbols) and p not in bare)) for u in facts.units)
    mates = tuple((a, b) for a, b in facts.mates if _inside(a, symbols) and _inside(b, symbols))
    far = tuple((a, b) for a, b in facts.far_ends if _inside(a, symbols))
    series = tuple(s for s in facts.series if set(leaves_of(s)) <= symbols)
    kept = tuple(c for c in (frozenset(s & symbols) for s in facts.keep_whole) if len(c) >= _MIN_ENDS)
    shown = (tuple(p for p in group if p not in bare and p not in gone) for group in facts.groups)
    groups = tuple(g for g in shown if len(g) >= _MIN_ENDS and any(_inside(p, symbols) for p in g))
    return Facts(kept, units, mates, series=series, far_ends=far, groups=groups)


def _known[T](names: Iterable[T], known: Collection[T]) -> bool:
    return all(n in known for n in names)


def _hints(hints: Hints, names: Collection[str], scope: DrawingScope) -> Hints:
    """The hints whose every name stands in the scope, and the scope's frames (R900 G9)."""
    return Hints(
        tuple(g for g in hints.group_order if g in names),
        tuple(p for p in hints.order_pairs if _known(p, names)),
        scope.frames,
    )


@dataclass(frozen=True, slots=True)
class Restriction:
    """One scope's problem, with the ids of the nets it drops (R520 B1)."""

    problem: PlacementProblem
    dropped: frozenset[str]


def _scoped(  # noqa: PLR0913, PLR0917 -- the scope cut takes the set's cut facts, as `restriction` does [R1867]
    problem: PlacementProblem,
    scope: DrawingScope,
    bare: Collection[PinRef],
    lines: Mapping[PinRef, str] | None,
    scopes: Sequence[DrawingScope],
    pieces: Mapping[PinRef, str],
) -> tuple[tuple[Net, ...], frozenset[str]]:
    """The scope's nets and the ids it drops."""
    boundary = {p for u in problem.facts.units for p in u.boundary}
    outward = _outward(problem.facts.mates, scope.symbols)
    own = scopes.index(scope) if scope in scopes else -1
    joined = {n.id for n in problem.nets if _joined(n, own, scopes)}
    ended = {*bare, *(a.pin for a in problem.anchors)}  # an anchored pin ends its net: no conductor leaves it
    cut = [(n, _net(n, scope.symbols, (boundary, ended, outward), problem.facts.far_ends, pieces)) for n in problem.nets if n.id not in joined]
    nets = tuple(_lined(p, lines or {}) for _, ps in cut for p in ps) + tuple(_whole(n, scope, boundary) for n in problem.nets if n.id in joined)
    dropped = frozenset(o.id for o, ps in cut if not ps and any(p.sym in scope.symbols for p in o.pins))
    return nets, dropped


def restriction(  # noqa: PLR0913 -- the scope's problem takes the set's cut facts and its options [R1867]
    problem: PlacementProblem,
    scope: DrawingScope,
    bare: Collection[PinRef] = (),
    lines: Mapping[PinRef, str] | None = None,
    scopes: Sequence[DrawingScope] = (),
    *,
    options: Options,
    tags: Mapping[str, Mapping[str, Size]],
    pieces: Mapping[PinRef, str] | None = None,
) -> Restriction:
    """The problem of one scope with its cut nets; the whole problem unchanged when it holds all.

    `scopes` are every set: a net they share a terminal of is whole where its ends stand (R652). Labels are the scope's own (`Sym.labels`).
    `bare` pins never end a cut; `lines` names one's line; `pieces` (`scopes.piece_names`) names each pin's piece: a cut net is one `Net` per piece.
    """
    home = "" if scope.of_unit is None else scope.of_unit.value  # a copy is paged with its set: its unit
    inside = tuple(replace(s, unit=home) if s.id in scope.away else s for s in problem.symbols if s.id in scope.symbols)
    if len(inside) == len(problem.symbols):
        return Restriction(
            replace(
                problem,
                symbols=inside,
                annexes=label_annexes(inside, options, home, tags),
                wider=wider_annexes(inside, options, home, tags),
                hints=replace(problem.hints, frames=scope.frames),
            ),
            frozenset(),
        )
    nets, dropped = _scoped(problem, scope, bare, lines, scopes, pieces or {})
    anchors = tuple(a for a in problem.anchors if a.pin.sym in scope.symbols)
    touched = {p.sym for n in nets for p in n.pins} | {a.pin.sym for a in anchors}
    syms = tuple(s for s in inside if s.id in touched)
    names = {s.id for s in syms} | {s.group for s in syms if s.group}
    gone = {p for n in problem.nets if n.id in dropped for p in n.pins}  # a dropped net draws no conductor and no stub (drawn_nets `blocked`)
    unit = {s.id: s.unit for s in problem.symbols}
    other = {i for i, u in unit.items() if u != home} - scope.symbols
    facts = _facts(_carried(problem.facts, scope, other, unit), frozenset(s.id for s in syms), bare, gone)
    annexes = label_annexes(syms, options, home, tags)
    part = PlacementProblem(
        problem.area,
        syms,
        nets,
        facts,
        _hints(problem.hints, names, scope),
        anchors,
        annexes,
        wider_annexes(syms, options, home, tags),
    )
    return Restriction(part, dropped)
