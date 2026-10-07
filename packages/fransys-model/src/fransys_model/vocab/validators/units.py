"""Validator: a unit's boundary (units spec U3, U4, U5)."""

from typing import TYPE_CHECKING, Any, Final

from fransys_model.kernel import Finding, Severity, key_text
from fransys_model.vocab.enums import FunctionKind, Gender
from fransys_model.vocab.facets.connector import ConnectorFacet
from fransys_model.vocab.joins import joined_ports
from fransys_model.vocab.membership import standalone as unit_standalone
from fransys_model.vocab.membership import units as unit_ids
from fransys_model.vocab.tables import (
    boundaries,
    conductors,
    facets_of,
    functions,
    items,
    mates,
    nets,
    ports,
    units,
    unused_boundaries,
)
from fransys_model.vocab.unit_index import unit_index

if TYPE_CHECKING:
    from collections.abc import Iterable

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Function, Item, Port, Unit

BOUNDARY_UNCONNECTED: Final[str] = "BOUNDARY_UNCONNECTED"
UNIT_BOUNDARY_BYPASSED: Final[str] = "UNIT_BOUNDARY_BYPASSED"
UNIT_CONNECTOR_DANGLING: Final[str] = "UNIT_CONNECTOR_DANGLING"
MATE_PORT_MISMATCH: Final[str] = "MATE_PORT_MISMATCH"
CONNECTOR_WIRED_WITHOUT_MATE: Final[str] = "CONNECTOR_WIRED_WITHOUT_MATE"
UNUSED_CONTRADICTED: Final[str] = "UNUSED_CONTRADICTED"
BOUNDARY_KIND: Final[str] = "BOUNDARY_KIND"
BOUNDARY_NOT_IN_UNIT: Final[str] = "BOUNDARY_NOT_IN_UNIT"
MATE_NOT_CONNECTOR: Final[str] = "MATE_NOT_CONNECTOR"

_BOUNDARY_KINDS: Final = frozenset({FunctionKind.TERMINAL, FunctionKind.CONNECTOR})
_GENDERED: Final = frozenset({Gender.MALE, Gender.FEMALE})


def _finding(code: str, severity: Severity, subjects: Iterable[Id[Any]], message: str) -> Finding:
    return Finding(code=code, severity=severity, subjects=tuple(subjects), message=message)


class _Plant:
    """The lookups every check shares, built once per model (units spec U4)."""

    def __init__(self, model: Model) -> None:
        self.model = model
        self.units = units(model)
        self.items = items(model)
        self.functions = functions(model)
        self.ports = ports(model)
        self.mates = mates(model)
        self.conductors = conductors(model)
        self.boundaries = boundaries(model)
        self.unused = unused_boundaries(model)
        self.all_units = unit_ids(model)
        index = unit_index(model)
        self.subtree_of = index.subtree_of
        self.containing = index.containing
        self.boundary_of = {unit: frozenset(found) for unit, found in index.boundary_of.items()}

        names: dict[Id[Function], set[str]] = {}
        self.ports_of_function: dict[Id[Function], list[Id[Port]]] = {}
        for port in self.ports.values():
            names.setdefault(port.function, set()).add(port.name)
            self.ports_of_function.setdefault(port.function, []).append(port.id)
        self.port_names = names
        # a port is on a mate when the partner function has a port of the same name
        self.mated = {
            (end, name)
            for mate in self.mates.values()
            for end, partner in ((mate.a, mate.b), (mate.b, mate.a))
            for name in names.get(end, set()) & names.get(partner, set())
        }
        wired = {
            port for conductor in self.conductors.values() for port in (conductor.a, conductor.b)
        }
        declared = {port for net in nets(model).values() for port in net.ports}
        self.connected_ports = wired | declared | joined_ports(model)
        facets = facets_of(model, ConnectorFacet)
        gender_of = {facet.subject: facet.gender for facet in facets.values()}
        self.gendered = {
            function.id: gender
            for function in self.functions.values()
            if function.template is not None
            and (gender := gender_of.get(function.template)) in _GENDERED
        }

        ends: list[tuple[Id[Function], Id[Item], Id[Item], Id[Any]]] = []
        for conductor in self.conductors.values():
            fn_a = self.ports[conductor.a].function
            fn_b = self.ports[conductor.b].function
            ends.extend(self._ends_of(fn_a, fn_b, conductor.id))
        for mate in self.mates.values():
            ends.extend(self._ends_of(mate.a, mate.b, mate.id))
        self.ends = ends
        self.ends_by_function: dict[Id[Function], list[tuple[Id[Item], Id[Item]]]] = {}
        for function, item, other, _record in ends:
            self.ends_by_function.setdefault(function, []).append((item, other))

    def _ends_of(
        self, fn_a: Id[Function], fn_b: Id[Function], record_id: Id[Any]
    ) -> list[tuple[Id[Function], Id[Item], Id[Item], Id[Any]]]:
        item_a, item_b = self.functions[fn_a].item, self.functions[fn_b].item
        return [(fn_a, item_a, item_b, record_id), (fn_b, item_b, item_a, record_id)]

    def item_unit(self, item: Id[Item]) -> Id[Unit] | None:
        return self.items[item].unit

    def crosses(self, subtree: frozenset[Id[Unit]], item: Id[Item], other: Id[Item]) -> bool:
        """Whether an end on `item` crosses out of the unit whose subtree is `subtree` (U4)."""
        return self.item_unit(item) in subtree and self.item_unit(other) not in subtree

    def crosses_out_of(self, unit: Id[Unit], function: Id[Function]) -> bool:
        """Whether at least one conductor or mate end on `function` crosses out of `unit` (U4).

        Declared `Net`s do not count (U4): `self.ends` is built from conductors and mates only.
        """
        subtree = self.subtree_of[unit]
        return any(
            self.crosses(subtree, item, other)
            for item, other in self.ends_by_function.get(function, ())
        )

    def port_connected(self, port_id: Id[Port]) -> bool:
        """Whether `port_id` carries a conductor, is in a declared net, or is on a mate."""
        port = self.ports[port_id]
        return port_id in self.connected_ports or (port.function, port.name) in self.mated


def _boundary_unconnected(plant: _Plant) -> list[Finding]:
    unused_functions = {unused.function for unused in plant.unused.values()}
    found = []
    for unit in plant.all_units:
        if unit_standalone(plant.model, unit):
            continue
        for function in plant.boundary_of[unit]:
            if plant.crosses_out_of(unit, function) or function in unused_functions:
                continue
            message = (
                f"boundary function {key_text(plant.functions[function])} of unit "
                f"{key_text(plant.units[unit])} is not connected across it and has no "
                "declared UnusedBoundary"
            )
            found.append(_finding(BOUNDARY_UNCONNECTED, Severity.ERROR, (unit, function), message))
    return found


def _unit_boundary_bypassed(plant: _Plant) -> list[Finding]:
    found = []
    for function, item, other, record in plant.ends:
        item_unit = plant.item_unit(item)
        crossable = (
            frozenset() if item_unit is None else plant.containing.get(item_unit, frozenset())
        )
        for unit in crossable:
            if not plant.crosses(plant.subtree_of[unit], item, other):
                continue
            if function in plant.boundary_of[unit]:
                continue
            message = (
                f"function {key_text(plant.functions[function])} crosses out of unit "
                f"{key_text(plant.units[unit])} without being its boundary"
            )
            found.append(
                _finding(UNIT_BOUNDARY_BYPASSED, Severity.ERROR, (unit, function, record), message)
            )
    return found


def _unit_connector_dangling(plant: _Plant) -> list[Finding]:
    found = []
    for function in plant.functions.values():
        item = plant.items[function.item]
        if item.unit is None or function.kind not in _BOUNDARY_KINDS:
            continue
        if function.id in plant.boundary_of[item.unit]:
            continue
        function_ports = plant.ports_of_function.get(function.id, [])
        if any(plant.port_connected(port_id) for port_id in function_ports):
            continue
        message = (
            f"{function.kind.value} function {key_text(function)} belongs directly to unit "
            f"{key_text(plant.units[item.unit])}, is not its boundary, and connects to nothing"
        )
        found.append(
            _finding(UNIT_CONNECTOR_DANGLING, Severity.WARNING, (item.unit, function.id), message)
        )
    return found


def _mate_port_mismatch(plant: _Plant) -> list[Finding]:
    found = []
    for mate in plant.mates.values():
        names_a = plant.port_names.get(mate.a, set())
        names_b = plant.port_names.get(mate.b, set())
        if names_a == names_b:
            continue
        unmatched = ", ".join(sorted(names_a ^ names_b))
        message = f"mate {key_text(mate)} joins ports named {unmatched} that have no match"
        found.append(
            _finding(MATE_PORT_MISMATCH, Severity.WARNING, (mate.id, mate.a, mate.b), message)
        )
    return found


def _mate_not_connector(plant: _Plant) -> list[Finding]:
    found = []
    for mate in plant.mates.values():
        for end in (mate.a, mate.b):
            function = plant.functions[end]
            if function.kind in _BOUNDARY_KINDS:
                continue
            message = (
                f"mate {key_text(mate)} has end {key_text(function)} of kind "
                f"{function.kind.value}, not connector or terminal"
            )
            found.append(_finding(MATE_NOT_CONNECTOR, Severity.ERROR, (mate.id, end), message))
    return found


def _connector_wired_without_mate(plant: _Plant) -> list[Finding]:
    found = []
    for function, item, other, record in plant.ends:
        if record not in plant.conductors or function not in plant.gendered:
            continue
        item_unit = plant.item_unit(item)
        if item_unit is None:
            continue
        for unit in plant.containing.get(item_unit, frozenset()):
            if function not in plant.boundary_of[unit]:
                continue
            if not plant.crosses(plant.subtree_of[unit], item, other):
                continue
            message = (
                f"a conductor lands directly on {key_text(plant.functions[function])}, the "
                f"{plant.gendered[function].value} boundary connector of unit "
                f"{key_text(plant.units[unit])}; wire a mating plug and mate it instead"
            )
            subjects = (unit, function, record)
            found.append(
                _finding(CONNECTOR_WIRED_WITHOUT_MATE, Severity.WARNING, subjects, message)
            )
    return found


def _unused_contradicted(plant: _Plant) -> list[Finding]:
    boundary_units_of: dict[Id[Function], list[Id[Unit]]] = {}
    for boundary in plant.boundaries.values():
        boundary_units_of.setdefault(boundary.function, []).append(boundary.unit)
    found = []
    for unused in plant.unused.values():
        function = unused.function
        owners = boundary_units_of.get(function, [])
        if not owners:
            message = (
                f"UnusedBoundary names {key_text(plant.functions[function])}, which is the "
                "boundary of no unit"
            )
            found.append(_finding(UNUSED_CONTRADICTED, Severity.WARNING, (function,), message))
            continue
        for unit in owners:
            if not plant.crosses_out_of(unit, function):
                continue
            message = (
                f"UnusedBoundary names {key_text(plant.functions[function])}, which is "
                f"connected across unit {key_text(plant.units[unit])} it is a boundary of"
            )
            found.append(_finding(UNUSED_CONTRADICTED, Severity.WARNING, (unit, function), message))
    return found


def _boundary_kind_and_membership(plant: _Plant) -> list[Finding]:
    found = []
    for boundary in plant.boundaries.values():
        function = plant.functions[boundary.function]
        if function.kind not in _BOUNDARY_KINDS:
            message = (
                f"boundary function {key_text(function)} has kind {function.kind.value}, not "
                "terminal or connector"
            )
            found.append(
                _finding(BOUNDARY_KIND, Severity.ERROR, (boundary.unit, boundary.function), message)
            )
        item_unit = plant.items[function.item].unit
        if item_unit not in plant.subtree_of[boundary.unit]:
            message = (
                f"boundary function {key_text(function)}'s item does not belong to unit "
                f"{key_text(plant.units[boundary.unit])}'s subtree"
            )
            subjects = (boundary.unit, boundary.function)
            found.append(_finding(BOUNDARY_NOT_IN_UNIT, Severity.ERROR, subjects, message))
    return found


def check_units(model: Model) -> tuple[Finding, ...]:
    """Check every unit's boundary and every mate's kind; `UNIT_CYCLE` is `check_structure`'s.

    `ERROR`: the boundary codes `BOUNDARY_UNCONNECTED`, `UNIT_BOUNDARY_BYPASSED`, `BOUNDARY_KIND`,
    `BOUNDARY_NOT_IN_UNIT`, and `MATE_NOT_CONNECTOR`; the others `WARNING`. Sorted by code.
    """
    plant = _Plant(model)
    found = [
        *_boundary_unconnected(plant),
        *_unit_boundary_bypassed(plant),
        *_unit_connector_dangling(plant),
        *_mate_port_mismatch(plant),
        *_mate_not_connector(plant),
        *_connector_wired_without_mate(plant),
        *_unused_contradicted(plant),
        *_boundary_kind_and_membership(plant),
    ]
    return tuple(sorted(found, key=lambda f: (f.code, f.subjects, f.message)))
