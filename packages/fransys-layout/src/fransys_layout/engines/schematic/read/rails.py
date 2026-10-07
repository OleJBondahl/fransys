"""V3 (layout-0099): rail terminals are not drawn; a pin wired to a rail draws its power symbol.

A rail terminal and the links bonding it leave the page. A conductor between a rail terminal and a
drawn pin, or between two drawn pins on power ports, is a rail wire: not drawn, and each drawn pin
end is a `RailEnd` that takes the rail's symbol. The terminal table reads the model, not this.
"""

import dataclasses
from typing import TYPE_CHECKING, Any

from fransys_layout.engines.schematic.read.units import boundary_edge_set
from fransys_layout.stages.types import Home, RailEnd
from fransys_model.derive import is_rail_terminal, port_power_kind, terminal_items
from fransys_model.vocab import PowerKind
from fransys_model.vocab.enums import ConductorKind
from fransys_model.vocab.membership import crosses_unit
from fransys_model.vocab.tables import functions as functions_table
from fransys_model.vocab.tables import ports as ports_table

if TYPE_CHECKING:
    from collections.abc import Collection

    from fransys_layout.stages.types import Connection, FunctionSpec, NetGroup, PortRef
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.connectivity import Conductor

_LINKS = frozenset({ConductorKind.BUSBAR, ConductorKind.RAIL})


def rail_terminal_functions(model: Model, specs: tuple[FunctionSpec, ...]) -> frozenset[Id[Any]]:
    """The functions of `specs` that are terminals of a rail terminal item."""
    return frozenset(
        spec.function
        for spec in specs
        if spec.kind == "terminal" and is_rail_terminal(model, spec.item)
    )


def mark_boundary_rails(
    model: Model, specs: tuple[FunctionSpec, ...], undrawn: Collection[Id[Any]]
) -> tuple[FunctionSpec, ...]:
    """RB2: `specs`, each rail terminal on a unit boundary marked `rail`: its parent draws it."""
    boundary = boundary_edge_set(model)
    return tuple(
        dataclasses.replace(spec, home=Home.ELSEWHERE)
        if spec.function in undrawn and spec.function in boundary
        else spec
        for spec in specs
    )


def is_rail_link(model: Model, conductor: Conductor) -> bool:
    """Whether `conductor` is a busbar or rail link with an end on a rail terminal."""
    return conductor.kind in _LINKS and any(
        is_rail_terminal(model, functions_table(model)[ports_table(model)[end].function].item)
        for end in (conductor.a, conductor.b)
    )


def rail_wires(
    model: Model,
    connections: tuple[Connection, ...],
    specs: tuple[FunctionSpec, ...],
    undrawn: Collection[Id[Any]],
) -> tuple[tuple[Connection, ...], tuple[RailEnd, ...]]:
    """`connections` without the rail wires, and the `RailEnd` of each drawn pin they leave."""
    strip_terminals = terminal_items(model)
    pins = {spec.function for spec in specs if spec.item not in strip_terminals}
    drawn = {spec.function for spec in specs} - set(undrawn)
    boundary = {spec.function for spec in specs if spec.home is Home.ELSEWHERE}
    kept: list[Connection] = []
    ends: list[RailEnd] = []
    for connection in connections:
        pair = (connection.a, connection.b)
        if _is_rail_wire(model, pair, pins, drawn, undrawn) and not _enters_unit(
            model, pair, boundary
        ):
            keep = drawn if any(ref.function in undrawn for ref in pair) else pins
            ends += [
                RailEnd(ref=ref, connection=connection.handle)
                for ref in pair
                if ref.function in keep
            ]
        else:
            kept.append(connection)
    return tuple(kept), tuple(sorted(ends, key=lambda end: (end.ref.port, end.connection)))


def _enters_unit(
    model: Model, pair: tuple[PortRef, PortRef], boundary: Collection[Id[Any]]
) -> bool:
    """RB2: a conductor from outside a unit to its boundary rail terminal is the parent's wire."""
    if not any(ref.function in boundary for ref in pair):
        return False
    one, other = (functions_table(model)[ref.function].item for ref in pair)
    return crosses_unit(model, one, other)


def _is_rail_wire(
    model: Model,
    pair: tuple[PortRef, PortRef],
    pins: Collection[Id[Any]],
    drawn: Collection[Id[Any]],
    undrawn: Collection[Id[Any]],
) -> bool:
    """One end a removed rail terminal and the other a drawn power end, or both ends power pins.

    The drawn end of a removed rail terminal's wire may be a strip terminal; two power ends may not.
    """
    if not any(ref.function in undrawn for ref in pair):
        return all(ref.function in pins and _on_power(model, ref) for ref in pair)
    return any(ref.function in drawn and _on_power(model, ref) for ref in pair)


def _on_power(model: Model, ref: PortRef) -> bool:
    return port_power_kind(model, ref.port) is not PowerKind.NONE


def rail_groups(
    groups: tuple[NetGroup, ...], undrawn: Collection[Id[Any]], ends: tuple[RailEnd, ...]
) -> tuple[NetGroup, ...]:
    """`groups` without ports of removed rail terminals and rail ends; a lone port is dropped."""
    gone = {end.ref.port for end in ends}
    found = []
    for group in groups:
        ports = tuple(
            ref for ref in group.ports if ref.function not in undrawn and ref.port not in gone
        )
        if len(ports) == len(group.ports):
            found.append(group)
        elif len(ports) > 1:
            found.append(dataclasses.replace(group, ports=ports))
    return tuple(found)
