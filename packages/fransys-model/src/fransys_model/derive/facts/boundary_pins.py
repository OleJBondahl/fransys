"""The one reader of `Boundary` as a unit's interface: its pins."""

from fransys_model.derive.facts.units import boundary
from fransys_model.derive.indexes import build_indexes
from fransys_model.derive.lookups import pin_order
from fransys_model.derive.port_marking import port_marking
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Port, Unit


def unit_boundary_pins(model: Model, unit: Id[Unit] | None) -> tuple[Id[Port], ...]:
    """The ports of `unit`'s boundary functions: functions in `Id` order, pins in pin order."""
    if unit is None:
        return ()
    ports_of = build_indexes(model).ports_by_function
    return tuple(
        port
        for function in boundary(model, unit)
        for port in sorted(
            ports_of.get(function, ()), key=lambda p: pin_order(port_marking(model, p), p)
        )
    )
