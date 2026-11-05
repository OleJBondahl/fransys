"""The drawing sets a function is drawn in: its own, and for a terminal each set its conductors reach.

A set is keyed `(unit, place)`: the unit of the function's item, else the item's place (R652).
A terminal wired to functions of other sets in its own document is drawn in each of them.
"""

from fransys_model.kernel import Id, Model
from fransys_model.vocab.aspects import AspectNode
from fransys_model.vocab.core import Function, Unit
from fransys_model.vocab.tables import ports

from .document_sets import printing_document
from .facts.roles import function_role
from .facts.unit_index import boundary_owners, item_unit
from .facts.units import unit_encloses
from .far_pins import far_pins
from .lookups import item_location
from .placement_reads import function_item, function_ports
from .power import is_rail_terminal

__all__ = ["ScopeKey", "function_abroad", "function_replicas", "function_scopes"]

type ScopeKey = tuple[Id[Unit] | None, Id[AspectNode] | None]


def _own(model: Model, function: Id[Function]) -> ScopeKey:
    item = function_item(model, function)
    unit = item_unit(model, item)
    return unit, None if unit is not None else item_location(model, item)


def _filed(model: Model, function: Id[Function]) -> tuple[tuple[ScopeKey, ...], frozenset[ScopeKey], frozenset[ScopeKey]]:
    """The sets that draw `function`; of them the replicas (sets of units enclosing the unit it bounds) and those abroad (another document)."""
    own = _own(model, function)
    if not function_role(model, function).terminal:
        return (own,), frozenset[ScopeKey](), frozenset[ScopeKey]()
    printer = printing_document(model, *own)
    owners = boundary_owners(model).get(function, ())
    bounds = own[0] if own[0] in owners else next(iter(owners), None)
    keys = [_own(model, ports(model)[far].function) for _, far in far_pins(model, function_ports(model, function))]
    replicas = frozenset(k for k in keys if bounds is not None and unit_encloses(model, k[0], bounds))
    reached = [k for k in keys if k in replicas or (printer is not None and printing_document(model, *k) == printer)]
    found = dict.fromkeys([own, *reached])
    if replicas and is_rail_terminal(model, function_item(model, function)):
        del found[own]
    return tuple(found), replicas, frozenset(k for k in found if printing_document(model, *k) != printer)


def function_scopes(model: Model, function: Id[Function]) -> tuple[ScopeKey, ...]:
    """The `(unit, place)` sets that draw `function`, its own first, then each other one a terminal reaches.

    A terminal is drawn in a set the same document prints as its own (UNIT-SCOPE), and a unit's
    boundary terminal in each set of an enclosing unit that it is wired from, whatever the document
    (UNIT-BOUNDARY-PINS). A boundary rail terminal stands in those sets only: its own unit shows the
    rail as a power symbol. A conductor into another document stays a stub.
    A far end always resolves to a port: freeze rejects a conductor whose end is not one.
    """
    return _filed(model, function)[0]


def function_replicas(model: Model, function: Id[Function]) -> frozenset[ScopeKey]:
    """The sets of `function`'s scopes that draw it as a unit boundary replica: such a set adds its group to the page title."""
    return _filed(model, function)[1]


def function_abroad(model: Model, function: Id[Function]) -> frozenset[ScopeKey]:
    """The sets of `function`'s scopes that print in another document than its own.

    A conductor into another document stays a stub; a same-document end draws no reference.
    """
    return _filed(model, function)[2]
