"""The drawing sets of the core path: one per location of the placed functions (PAGE-02, Ruling 50).

`drawing_scopes` splits the kit's symbols by the location of their function; `restriction` cuts the
whole problem down to one scope. A net cut by a scope keeps its in-set pins and ends in a stub.
"""

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from fransys_layout.core import CutEnd, Facts, Hints, PlacementProblem, leaves_of
from fransys_model.derive import (
    far_pins,
    function_abroad,
    function_is_idle_terminal,
    function_item,
    function_replicas,
    function_scopes,
    item_unit,
    port_function,
    stub_far,
    unit_index,
    unit_location,
    unit_parent,
)
from fransys_model.derive.drawing_text import external_frame_title, outline_title
from fransys_model.derive.order import locations_in_order, units_in_order
from fransys_model.kernel import render_id

from .kit_keys import function_of
from .placement_annexes import label_annexes, wider_annexes
from .placement_ids import symbol_key
from .placement_markers import pin_ports

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Mapping, Sequence

    from fransys_layout.core import Net, Options, PagePlan, PinRef, Size
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import AspectNode, Unit

    from .placement_kit import PickKey, SymbolKit

__all__ = [
    "DrawingScope",
    "Restriction",
    "bare_pins",
    "cut_lines",
    "drawing_scopes",
    "frame_titles",
    "restriction",
    "scope_groups",
]

_MIN_ENDS = 2  # a wire needs two ends


@dataclass(frozen=True, slots=True)
class DrawingScope:
    """One drawing set: its unit (`None` for the top level), its location and its symbol ids."""

    of_unit: Id[Unit] | None
    location: Id[AspectNode] | None
    symbols: frozenset[str]
    copies: frozenset[str] = frozenset()
    replicas: frozenset[str] = frozenset()
    abroad: frozenset[str] = frozenset()
    frames: tuple[tuple[str, frozenset[str]], ...] = ()

    @property
    def away(self) -> frozenset[str]:
        """The symbols drawn here but homed in another set: copies and replicas."""
        return self.copies | self.replicas


type _Filed = dict[tuple[Id[Unit] | None, Id[AspectNode] | None], set[str]]


def _filed(model: Model, kit: SymbolKit) -> tuple[_Filed, _Filed, _Filed, _Filed]:
    """The symbols each set draws, of them the copies, the replicas and the ends printed in another document."""
    found: _Filed = {}
    copied: _Filed = {}
    replicated: _Filed = {}
    abroad: _Filed = {}
    for function in kit:
        home, *copies = function_scopes(model, function_of(model, function))
        replicas = function_replicas(model, function_of(model, function))
        for key in function_abroad(model, function_of(model, function)):
            abroad.setdefault(key, set()).add(symbol_key(model, function))
        key_of = symbol_key(model, function)
        for key in (home, *copies):
            found.setdefault(key, set()).add(key_of)
            if key in replicas:
                replicated.setdefault(key, set()).add(key_of)
            elif key != home:
                copied.setdefault(key, set()).add(key_of)
    return found, copied, replicated, abroad


type _Framed = dict[tuple[Id[Unit] | None, Id[AspectNode] | None], dict[str, set[str]]]


def home_unit(model: Model, function: PickKey) -> Id[Unit] | None:
    """The unit of a function's item: its own, never a scope it is drawn in as a rail replica (R830)."""
    return item_unit(model, function_item(model, function_of(model, function)))


def frame_titles(model: Model, kit: SymbolKit) -> dict[str, tuple[str, str]]:
    """Each frame key `DrawingScope.frames` holds -> its es symbol key and its title: a unit's, or the external root's own, empty by default."""
    roots = unit_index(model).external_root
    found: dict[str, tuple[str, str]] = {}
    for function in kit:
        if (home := home_unit(model, function)) is not None:
            found[render_id(home)] = ("unit-outline", outline_title(model, home))
        if (root := roots.get(function_item(model, function_of(model, function)))) is not None:
            found[render_id(root)] = ("unit-outline-by-others", external_frame_title())
    return found


def _replica_frames(model: Model, function: PickKey, found: _Framed) -> None:
    """File `function`'s symbol under its home unit's frame in each unit set that draws it as a replica (R900 G9)."""
    home = home_unit(model, function)
    for key in function_replicas(model, function_of(model, function)):
        if home is not None and key[0] is not None:
            found.setdefault(key, {}).setdefault(render_id(home), set()).add(symbol_key(model, function))


def _external_frames(model: Model, function: PickKey, found: _Framed) -> None:
    """File an external `function`'s symbol under its root's frame in each set of a page with no unit above it (UNIT-SCOPE, R631 B6)."""
    root = unit_index(model).external_root.get(function_item(model, function_of(model, function)))
    if root is None:
        return
    for key in function_scopes(model, function_of(model, function)):
        if key[0] is None or unit_parent(model, key[0]) is None:
            found.setdefault(key, {}).setdefault(render_id(root), set()).add(symbol_key(model, function))


def _framed(model: Model, kit: SymbolKit) -> _Framed:
    """Per set, the symbols it draws grouped by frame key: replicas by their own unit (never a place set, R833), external symbols by their root."""
    found: _Framed = {}
    for function in kit:
        _replica_frames(model, function, found)
        _external_frames(model, function, found)
    return found


def drawing_scopes(model: Model, kit: SymbolKit) -> tuple[DrawingScope, ...]:
    """The scopes of the kit's functions, filed as today's engine files them (layout-0081).

    Top level first: by location in `derive.order` order, no location last. Then one set per unit
    in `units_in_order`, at the unit's own location; a unit's functions are never split by place.
    """
    found, copied, replicated, abroad = _filed(model, kit)
    framed = _framed(model, kit)
    located = locations_in_order(model, (p for u, p in found if u is None and p is not None))
    top = [*located, *([None] if (None, None) in found else [])]
    keys = [(None, place) for place in top]
    keys += [(unit, None) for unit in units_in_order(model, (u for u, _ in found if u is not None))]
    return tuple(
        DrawingScope(
            unit,
            place if unit is None else unit_location(model, unit),
            frozenset(found[unit, place]),
            frozenset(copied.get((unit, place), ())),
            frozenset(replicated.get((unit, place), ())),
            frozenset(abroad.get((unit, place), ())),
            tuple((k, frozenset(s)) for k, s in framed.get((unit, place), {}).items()),
        )
        for unit, place in keys
    )


def bare_pins(model: Model, kit: SymbolKit) -> frozenset[PinRef]:
    """The pins a cut net never ends at: none leaves them by a conductor, or an unreached terminal.

    No conductor leaves a pin when `derive.far_pins` finds none at its ports: its function's through path is no conductor (R1544). A
    terminal no wire inside its drawing reaches is drawn only by its table (L7).
    """
    found = set()
    for pin, names in pin_ports(model, kit).items():
        function = port_function(model, names[0])
        idle = function is not None and function_is_idle_terminal(model, function)
        if idle or not far_pins(model, names):
            found.add(pin)
    return frozenset(found)


def cut_lines(model: Model, kit: SymbolKit) -> Mapping[PinRef, str]:
    """The line each pin leaves by: the harness `derive.stub_far` names and the connector it joins.

    The pins of one connector of one harness are one line (R481); a pin with no harness has none.
    """
    found = {}
    for pin, names in pin_ports(model, kit).items():
        ends = stub_far(model, names)
        function = port_function(model, names[0])
        if ends and ends[0][2] is not None and function is not None:
            found[pin] = f"{ends[0][2].value}/{function.value}"
    return found


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
) -> Net | None:
    """`net` with the pins inside `symbols`, `None` when none is inside or a cut one has no carrier.

    A net the scope cuts keeps its in-set pins and names in `cut` the one that continues outside.
    `carry` is the `_carriers` boundary, bare and outward pins; `ends` the far ends, to find a conductor between in-set pins.
    """
    pins = tuple(p for p in net.pins if p.sym in symbols)
    if not pins:
        return None
    if len(pins) == len(net.pins):
        return net
    cut = _carriers(pins, *carry)
    if not cut:
        return None
    if len({p.sym for p in pins}) == 1 and not any(a in pins and b in pins for a, b in ends):
        pins = cut  # one symbol's pins joined by no conductor need no wire between them: only the stub is drawn
    return replace(net, pins=pins, cut=tuple(CutEnd(p) for p in cut))


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


def _scoped(
    problem: PlacementProblem,
    scope: DrawingScope,
    bare: Collection[PinRef],
    lines: Mapping[PinRef, str] | None,
    scopes: Sequence[DrawingScope],
) -> tuple[tuple[Net, ...], frozenset[str]]:
    """The scope's nets and the ids it drops."""
    boundary = {p for u in problem.facts.units for p in u.boundary}
    outward = _outward(problem.facts.mates, scope.symbols)
    own = scopes.index(scope) if scope in scopes else -1
    joined = {n.id for n in problem.nets if _joined(n, own, scopes)}
    ended = {*bare, *(a.pin for a in problem.anchors)}  # an anchored pin ends its net: no conductor leaves it
    cut = [(n, _net(n, scope.symbols, (boundary, ended, outward), problem.facts.far_ends)) for n in problem.nets if n.id not in joined]
    nets = tuple(_lined(n, lines or {}) for _, n in cut if n is not None) + tuple(_whole(n, scope, boundary) for n in problem.nets if n.id in joined)
    dropped = frozenset(o.id for o, n in cut if n is None and any(p.sym in scope.symbols for p in o.pins))
    return nets, dropped


def scope_groups(pages: tuple[PagePlan, ...], problem: PlacementProblem, scope: DrawingScope) -> tuple[PagePlan, ...]:
    """`pages` with the groups `write_pages` records (page title, role, key): a group only copies of `scope` carry is off (R734 G6, R747)."""
    own = {s.group for s in problem.symbols if s.id not in scope.copies}
    skip = {s.group for s in problem.symbols if s.id in scope.copies} - own
    return tuple(replace(p, groups=tuple(g for g in p.groups if g not in skip)) for p in pages)


def restriction(  # noqa: PLR0913 -- the scope's problem takes the set's cut facts and its options [R1867]
    problem: PlacementProblem,
    scope: DrawingScope,
    bare: Collection[PinRef] = (),
    lines: Mapping[PinRef, str] | None = None,
    scopes: Sequence[DrawingScope] = (),
    *,
    options: Options,
    tags: Mapping[str, Mapping[str, Size]],
) -> Restriction:
    """The problem of one scope with its cut nets; the whole problem unchanged when it holds all.

    `scopes` are every set: a net they share a terminal of is whole where its ends stand (R652).
    Labels are the scope's own (`Sym.labels`), annexes made again with `options`. `bare` pins never end a cut; `lines` names one's line.
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
    nets, dropped = _scoped(problem, scope, bare, lines, scopes)
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
