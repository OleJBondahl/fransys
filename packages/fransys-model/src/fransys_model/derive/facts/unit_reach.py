"""What a container reads of a complete unit: its wired ports inside and out, its offers (EL-7).

Facts over any `HasTables`, so the author asks them of a draft view at `d.add` (spec M4); each
is uncached on a view.
"""

from fransys_model.derive.facts.children import unit_parent
from fransys_model.derive.facts.closure import port_item
from fransys_model.derive.facts.units import boundary, crosses_unit
from fransys_model.vocab.tables import HasTables, conductors, units, unused_boundaries
lazy from fransys_model.kernel import Id
lazy from fransys_model.vocab.core import Function, Port, Unit


def wired_inside_outside(model: HasTables) -> tuple[frozenset[Id[Port]], frozenset[Id[Port]]]:
    """The ports a conductor ties within one unit, and those it ties across a unit boundary."""
    inside: set[Id[Port]] = set()
    outside: set[Id[Port]] = set()
    for conductor in conductors(model).values():
        for end, other in ((conductor.a, conductor.b), (conductor.b, conductor.a)):
            crossing = crosses_unit(model, port_item(model, end), port_item(model, other))
            (outside if crossing else inside).add(end)
    return frozenset(inside), frozenset(outside)


def unused_functions(model: HasTables) -> frozenset[Id[Function]]:
    """The functions declared unused on purpose (`UnusedBoundary`)."""
    return frozenset(record.function for record in unused_boundaries(model).values())


def nested_boundary_functions(model: HasTables, unit: Id[Unit] | None) -> frozenset[Id[Function]]:
    """The boundary functions of the units nested directly in `unit`."""
    nested = (child for child in units(model) if unit_parent(model, child) == unit)
    return frozenset(function for child in nested for function in boundary(model, child))
