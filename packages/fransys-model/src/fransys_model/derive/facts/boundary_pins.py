"""The one reader of `Boundary` as a unit's interface: its functions and its pins."""

from fransys_model.derive.indexes import build_indexes
from fransys_model.derive.lookups import pin_order
from fransys_model.derive.port_marking import port_marking
from fransys_model.vocab.unit_index import unit_index
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Function, Port, Unit


def unit_boundary_functions(model: Model, unit: Id[Unit] | None) -> tuple[Id[Function], ...]:
    """The functions that are a boundary of `unit`, in `Id` order; empty for no unit.

    A pass-through function is a `Boundary` of each unit that offers it, so it
    is listed for the nested and the enclosing unit alike.
    """
    if unit is None:
        return ()
    return unit_index(model).boundary_of.get(unit, ())


def unit_boundary_pins(model: Model, unit: Id[Unit] | None) -> tuple[Id[Port], ...]:
    """The ports of `unit`'s boundary functions: functions in `Id` order, pins in pin order."""
    ports_of = build_indexes(model).ports_by_function
    return tuple(
        port
        for function in unit_boundary_functions(model, unit)
        for port in sorted(
            ports_of.get(function, ()), key=lambda p: pin_order(port_marking(model, p), p)
        )
    )
