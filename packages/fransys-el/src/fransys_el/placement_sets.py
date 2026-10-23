"""The drawing sets of the core path: one per location of the placed functions (PAGE-02, Ruling 50).

`drawing_scopes` splits the kit's symbols by the location of their function; `restrict` cuts the
whole problem down to one scope. A net cut by a scope keeps its in-set pins and ends in a stub.
"""

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from fransys_layout.core import CutEnd, Facts, Hints, PlacementProblem
from fransys_model.derive import (
    function_is_reached,
    function_item,
    function_role,
    item_location,
    item_unit,
    port_function,
    unit_location,
)
from fransys_model.derive.order import locations_in_order, units_in_order

from .kit_keys import function_of
from .placement_ids import symbol_key
from .placement_markers import pin_ports
from .placement_series import leaves
from .write_stubs import stub_ends

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Mapping

    from fransys_layout.core import Net, PinRef
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import AspectNode, Function, Unit

    from .placement_kit import SymbolKit

__all__ = ["DrawingScope", "bare_pins", "cut_lines", "drawing_scopes", "restrict"]

_MIN_ENDS = 2  # a wire needs two ends


@dataclass(frozen=True, slots=True)
class DrawingScope:
    """One drawing set: its unit (`None` for the top level), its location and its symbol ids."""

    of_unit: Id[Unit] | None
    location: Id[AspectNode] | None
    symbols: frozenset[str]


def drawing_scopes(model: Model, kit: SymbolKit) -> tuple[DrawingScope, ...]:
    """The scopes of the kit's functions, filed as today's engine files them (layout-0081).

    Top level first: by location in `derive.order` order, no location last. Then one set per unit
    in `units_in_order`, at the unit's own location; a unit's functions are never split by place.
    """
    found: dict[tuple[Id[Unit] | None, Id[AspectNode] | None], set[str]] = {}
    for function in kit:
        item = function_item(model, function_of(model, function))
        unit = item_unit(model, item)
        place = None if unit is not None else item_location(model, item)
        found.setdefault((unit, place), set()).add(symbol_key(model, function))
    located = locations_in_order(model, (p for u, p in found if u is None and p is not None))
    top = [*located, *([None] if (None, None) in found else [])]
    keys = [(None, place) for place in top]
    keys += [(unit, None) for unit in units_in_order(model, (u for u, _ in found if u is not None))]
    return tuple(
        DrawingScope(
            unit,
            place if unit is None else unit_location(model, unit),
            frozenset(found[unit, place]),
        )
        for unit, place in keys
    )


def _idle_terminal(model: Model, function: Id[Function]) -> bool:
    return function_role(model, function).terminal and not function_is_reached(model, function)


def bare_pins(model: Model, kit: SymbolKit) -> frozenset[PinRef]:
    """The pins a cut net never ends at: none leaves them by a conductor, or an unreached terminal.

    No conductor leaves a pin when `stub_ends` finds none (not even through its mate). A
    terminal no wire inside its drawing reaches is drawn only by its table (L7).
    """
    found = set()
    for pin, names in pin_ports(model, kit).items():
        function = port_function(model, names[0])
        idle = function is not None and _idle_terminal(model, function)
        if idle or stub_ends(model, names) is None:
            found.add(pin)
    return frozenset(found)


def cut_lines(model: Model, kit: SymbolKit) -> Mapping[PinRef, str]:
    """The line each pin leaves by: the harness `derive.stub_far` names and the connector it joins.

    The pins of one connector of one harness are one line (R481); a pin with no harness has none.
    """
    found = {}
    for pin, names in pin_ports(model, kit).items():
        ends = stub_ends(model, names)
        function = port_function(model, names[0])
        if ends is not None and ends[2] is not None and function is not None:
            found[pin] = f"{ends[2].value}/{function.value}"
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


def _net(
    net: Net,
    symbols: Collection[str],
    boundary: Collection[PinRef],
    bare: Collection[PinRef],
    outward: Collection[PinRef],
) -> Net | None:
    """`net` with the pins inside `symbols`, `None` when none is inside or a cut one has no carrier.

    A net the scope cuts keeps its in-set pins and names in `cut` the one that continues outside.
    """
    pins = tuple(p for p in net.pins if p.sym in symbols)
    if not pins:
        return None
    if len(pins) == len(net.pins):
        return net
    cut = _carriers(pins, boundary, bare, outward)
    if not cut:
        return None
    if len({p.sym for p in pins}) == 1:
        pins = cut  # one symbol's pins need no wire between them: only the stub is drawn
    return replace(net, pins=pins, cut=tuple(CutEnd(p) for p in cut))


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


def _facts(facts: Facts, symbols: frozenset[str], bare: Collection[PinRef]) -> Facts:
    """The facts of one scope: each set cut to its symbols, each boundary and mate inside.

    A boundary pin in `bare` has no conductor to name a stub's far end, so it is left out. A series
    region with a symbol outside is dropped: its neighbours share no net here.
    """
    cut = (frozenset(s & symbols) for s in facts.keep_whole)
    units = tuple(
        replace(u, boundary=tuple(p for p in u.boundary if _inside(p, symbols) and p not in bare))
        for u in facts.units
    )
    mates = tuple((a, b) for a, b in facts.mates if _inside(a, symbols) and _inside(b, symbols))
    series = tuple(s for s in facts.series if set(leaves(s)) <= symbols)
    return Facts(tuple(s for s in cut if len(s) >= _MIN_ENDS), units, mates, series=series)


def _known[T](names: Iterable[T], known: Collection[T]) -> bool:
    return all(n in known for n in names)


def _hints(hints: Hints, names: Collection[str], symbols: Collection[str]) -> Hints:
    """The hints whose every name stands in the scope."""
    return Hints(
        tuple(g for g in hints.group_order if g in names),
        frozenset(n for n in hints.break_before if n in names),
        tuple(s for s in hints.keep_together if _known(s, names)),
        tuple(p for p in hints.order_pairs if _known(p, names)),
        tuple(c for c in hints.chains if _known(c, names)),
        tuple(d for d in hints.draw_in if _known(d, names)),
        tuple(s for s in hints.sides if _inside(s[0], symbols)),
    )


def restrict(
    problem: PlacementProblem,
    scope: DrawingScope,
    bare: Collection[PinRef] = (),
    lines: Mapping[PinRef, str] | None = None,
) -> PlacementProblem:
    """The problem of one scope; the whole problem unchanged when the scope holds every symbol.

    `bare` pins (no conductor leaves) never end a cut; `lines` names a cut pin's line (`cut_lines`).
    A symbol the scope's nets and anchors no longer touch is left out, as `without_loose` does.
    """
    inside = tuple(s for s in problem.symbols if s.id in scope.symbols)
    if len(inside) == len(problem.symbols):
        return problem
    boundary = {p for u in problem.facts.units for p in u.boundary}
    outward = _outward(problem.facts.mates, scope.symbols)
    cut = (_net(n, scope.symbols, boundary, bare, outward) for n in problem.nets)
    nets = tuple(_lined(n, lines or {}) for n in cut if n is not None)
    anchors = tuple(a for a in problem.anchors if a.pin.sym in scope.symbols)
    touched = {p.sym for n in nets for p in n.pins} | {a.pin.sym for a in anchors}
    syms = tuple(s for s in inside if s.id in touched)
    names = {s.id for s in syms} | {s.group for s in syms if s.group}
    facts = _facts(problem.facts, frozenset(s.id for s in syms), bare)
    annexes = tuple(a for a in problem.annexes if a.owner in names)
    return PlacementProblem(
        problem.area,
        syms,
        nets,
        facts,
        _hints(problem.hints, names, scope.symbols),
        anchors,
        annexes,
    )
