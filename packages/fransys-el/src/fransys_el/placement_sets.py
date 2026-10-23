"""The drawing sets of the core path: one per location of the placed functions (PAGE-02, Ruling 50).

`drawing_scopes` splits the kit's symbols by the location of their function; `restrict` cuts the
whole problem down to one scope. A net with fewer than two pins in a scope is left out of it.
"""

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from fransys_layout.core import Facts, Hints, PlacementProblem
from fransys_model.derive import function_item, item_location, item_unit, unit_location
from fransys_model.derive.order import locations_in_order, units_in_order

from .kit_keys import function_of
from .placement_ids import symbol_key
from .placement_series import within

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable

    from fransys_layout.core import Net, PinRef
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import AspectNode, Unit

    from .placement_kit import SymbolKit

__all__ = ["DrawingScope", "drawing_scopes", "restrict"]

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


def _net(net: Net, symbols: Collection[str]) -> Net | None:
    """`net` with the pins inside `symbols`, or `None` when it is cut to one symbol or none.

    A net the scope holds whole may sit on one symbol (a bridge); a cut one needs two symbols.
    """
    pins = tuple(p for p in net.pins if p.sym in symbols)
    whole = len(pins) == len(net.pins)
    if len(pins) < _MIN_ENDS or not (whole or len({p.sym for p in pins}) >= _MIN_ENDS):
        return None
    return replace(net, pins=pins)


def _inside(pin: PinRef, symbols: Collection[str]) -> bool:
    return pin.sym in symbols


def _facts(facts: Facts, symbols: frozenset[str]) -> Facts:
    """The facts of one scope: each set cut to its symbols, each boundary and mate inside."""
    cut = (frozenset(s & symbols) for s in facts.keep_whole)
    units = tuple(
        replace(u, boundary=tuple(p for p in u.boundary if _inside(p, symbols)))
        for u in facts.units
    )
    mates = tuple((a, b) for a, b in facts.mates if _inside(a, symbols) and _inside(b, symbols))
    series = tuple(c for s in facts.series if (c := within(s, symbols)) is not None)
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


def restrict(problem: PlacementProblem, scope: DrawingScope) -> PlacementProblem:
    """The problem of one scope; the whole problem unchanged when the scope holds every symbol.

    A symbol the scope's nets and anchors no longer touch is left out, as `without_loose` does.
    """
    inside = tuple(s for s in problem.symbols if s.id in scope.symbols)
    if len(inside) == len(problem.symbols):
        return problem
    nets = tuple(n for n in (_net(n, scope.symbols) for n in problem.nets) if n is not None)
    anchors = tuple(a for a in problem.anchors if a.pin.sym in scope.symbols)
    touched = {p.sym for n in nets for p in n.pins} | {a.pin.sym for a in anchors}
    syms = tuple(s for s in inside if s.id in touched)
    names = {s.id for s in syms} | {s.group for s in syms if s.group}
    facts = _facts(problem.facts, frozenset(s.id for s in syms))
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
