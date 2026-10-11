"""A unit's boundary function that is no terminal or connector: its wired ports as pin cells.

model-0188: the parent's black box shows each such port as a pin view (R7 A), as it shows a
connector's, never the item box or the symbol. The function stays drawn whole on the unit's own
pages; only a wire from outside the unit ends on the pin view, whose handle is its port's (R7 A).
"""

import dataclasses
from typing import TYPE_CHECKING, Any

from fransys_layout.engines.schematic.defaults import kind_roles
from fransys_layout.stages.types import Home
from fransys_model.vocab.membership import boundary, units
from fransys_model.vocab.tables import functions as functions_table
from fransys_model.vocab.unit_index import unit_index

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from fransys_layout.stages import Connection, FunctionSpec, PortRef
    from fransys_model.kernel import Id, Model

_OWN_VIEWS = frozenset({"terminal", "connector"})

type Landings = dict[tuple[Id[Any], Id[Any]], Id[Any]]


def pin_landings(
    model: Model, specs: Iterable[FunctionSpec], connections: Iterable[Connection]
) -> Landings:
    """Each (conductor, port) end on a boundary function's port from outside: its pin view."""
    kinds = {spec.function: spec.kind for spec in specs}
    held: dict[Id[Any], list[Id[Any]]] = {}
    for unit in units(model):
        for function in boundary(model, unit):
            if kinds.get(function, "terminal") not in _OWN_VIEWS:
                held.setdefault(function, []).append(unit)
    return {
        (wire.handle, end.port): end.port
        for wire in connections
        for end, far in ((wire.a, wire.b), (wire.b, wire.a))
        if end.function in held and _outside(model, held[end.function], far)
    }


def _outside(model: Model, boundary_units: Sequence[Id[Any]], far: PortRef) -> bool:
    """Whether the far end's item is outside the subtree of one of the units."""
    record = functions_table(model).get(far.function)
    item = None if record is None else record.item
    inside = unit_index(model).items_of
    return any(item not in inside[unit] for unit in boundary_units)


def land_on_pins(
    connections: Iterable[Connection], landings: Mapping[Any, Id[Any]]
) -> tuple[Connection, ...]:
    """`connections`, each landing end named by its pin view."""
    return tuple(
        dataclasses.replace(
            wire, a=_landed(wire, wire.a, landings), b=_landed(wire, wire.b, landings)
        )
        for wire in connections
    )


def _landed(wire: Connection, end: PortRef, landings: Mapping[Any, Id[Any]]) -> PortRef:
    """`end`, on its pin view when `landings` has it."""
    pin = landings.get((wire.handle, end.port))
    return end if pin is None else dataclasses.replace(end, function=pin)


def pin_ports(landings: Mapping[Any, Id[Any]]) -> dict[Id[Any], Id[Any]]:
    """Each pin view's boundary port."""
    return {pin: port for (_, port), pin in landings.items()}


def pin_specs(
    specs: Iterable[FunctionSpec], landings: Mapping[Any, Id[Any]]
) -> tuple[FunctionSpec, ...]:
    """One pin view per landed port, drawn only in the parent (`Home.ELSEWHERE`)."""
    landed = set(pin_ports(landings).values())
    return tuple(
        dataclasses.replace(
            spec,
            function=port.port,
            key=(*spec.key, "pin", port.name),
            kind="connector",
            roles=kind_roles("connector"),
            category=None,
            part=None,  # the part's symbol choice is the function's, not its pin cell's
            poles=1,
            pole_pairs=(),
            ports=(dataclasses.replace(port, name="in"),),
            pin_function=spec.function,
            home=Home.ELSEWHERE,
        )
        for spec in specs
        for port in spec.ports
        if port.port in landed
    )
