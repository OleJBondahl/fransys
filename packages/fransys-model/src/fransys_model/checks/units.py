"""Validator: a unit's boundary."""

from typing import TYPE_CHECKING, Final

from fransys_model.checks._finding import ordered
from fransys_model.derive.facts.cores import is_core
from fransys_model.derive.facts.mates import unmatched_port_names
from fransys_model.derive.facts.net_crossings import crossing_functions, earth_carried_functions, net_crossings
from fransys_model.derive.facts.roles import function_role
from fransys_model.derive.facts.unit_crossings import (
    carried_unit,
    crossed_units,
    crosses_out_of,
    declared_owners,
    ends,
    function_gender,
    open_boundaries,
)
from fransys_model.derive.facts.unit_index import boundary_owners, boundary_unit, unit_index
from fransys_model.derive.facts.units import declared_unit
from fransys_model.derive.facts.wired_ports import mated_ports, wired_ports
from fransys_model.kernel import Finding, natural_join
from fransys_model.vocab.codes import finding
from fransys_model.vocab.finding_ref import ref
from fransys_model.vocab.tables import (
    boundaries,
    conductors,
    functions,
    items,
    mates,
    nets,
    ports,
    unused_boundaries,
    unused_ports,
)

if TYPE_CHECKING:
    from fransys_model.kernel import Model

BOUNDARY_UNCONNECTED: Final[str] = "BOUNDARY_UNCONNECTED"
NET_ACROSS_UNIT_BOUNDARY_OPEN: Final[str] = "NET_ACROSS_UNIT_BOUNDARY_OPEN"
NET_ACROSS_UNIT_BOUNDARY_JOINED: Final[str] = "NET_ACROSS_UNIT_BOUNDARY_JOINED"
UNIT_BOUNDARY_BYPASSED: Final[str] = "UNIT_BOUNDARY_BYPASSED"
MATE_PORT_MISMATCH: Final[str] = "MATE_PORT_MISMATCH"
CONNECTOR_WIRED_WITHOUT_MATE: Final[str] = "CONNECTOR_WIRED_WITHOUT_MATE"
UNUSED_CONTRADICTED: Final[str] = "UNUSED_CONTRADICTED"
BOUNDARY_NOT_IN_UNIT: Final[str] = "BOUNDARY_NOT_IN_UNIT"
MATE_NOT_CONNECTOR: Final[str] = "MATE_NOT_CONNECTOR"
UNUSED_NOT_BOUNDARY: Final[str] = "UNUSED_NOT_BOUNDARY"
UNUSED_POINT_WIRED: Final[str] = "UNUSED_POINT_WIRED"


def _boundary_unconnected(model: Model) -> list[Finding]:
    """A net that crosses the boundary has its own finding, `NET_ACROSS_UNIT_BOUNDARY_*`; an earth net needs none."""
    carried = crossing_functions(model) | earth_carried_functions(model)
    found = []
    for unit, function in open_boundaries(model):
        if function in carried:
            continue
        message = f"boundary function {ref(function)} of {ref(unit)} is not connected across it and has no declared UnusedBoundary"
        found.append(finding(BOUNDARY_UNCONNECTED, (unit, function), message))
    return found


def _net_across_unit_boundary(model: Model) -> list[Finding]:
    """One finding per net with pins in two units that no conductor or mate joins (layout-0322).

    `_OPEN` when a boundary pin of the net is joined across by nothing else, else `_JOINED`.
    """
    open_functions = {function for _, function in open_boundaries(model)}
    all_ports = ports(model)
    found = []
    for net_id, held in net_crossings(model).items():
        pins = natural_join(ref(all_ports[port]) for port in held)
        net = nets(model)[net_id]
        message = f"net {net.name or ref(net)} joins pins in different units ({pins}); a net does not cross a unit boundary"
        open_pin = any(all_ports[port].function in open_functions for port in held)
        code = NET_ACROSS_UNIT_BOUNDARY_OPEN if open_pin else NET_ACROSS_UNIT_BOUNDARY_JOINED
        found.append(finding(code, (net_id, *held), message))
    return found


def _unit_boundary_bypassed(model: Model) -> list[Finding]:
    boundary_of = unit_index(model).boundary_of
    found = []
    for function, item, other, record in ends(model):
        for unit in crossed_units(model, item, other):
            if function in boundary_of[unit]:
                continue
            message = f"function {ref(function)} crosses out of {ref(unit)} without being its boundary"
            subjects = (unit, function, record)
            found.append(finding(UNIT_BOUNDARY_BYPASSED, subjects, message))
    return found


def _mate_port_mismatch(model: Model) -> list[Finding]:
    found = []
    for mate in mates(model).values():
        unmatched = unmatched_port_names(model, mate.id)
        if not unmatched:
            continue
        message = f"mate {ref(mate)} joins ports named {natural_join(unmatched)} that have no match"
        found.append(finding(MATE_PORT_MISMATCH, (mate.id, mate.a, mate.b), message))
    return found


def _mate_not_connector(model: Model) -> list[Finding]:
    found = []
    for mate in mates(model).values():
        for end in (mate.a, mate.b):
            function = functions(model)[end]
            role = function_role(model, end)
            if role.terminal or role.pin_group:
                continue
            message = f"mate {ref(mate)} has end {ref(function)} of kind {function.kind.value}, not connector or terminal"
            found.append(finding(MATE_NOT_CONNECTOR, (mate.id, end), message))
    return found


def _connector_wired_without_mate(model: Model) -> list[Finding]:
    boundary_of = unit_index(model).boundary_of
    wires = conductors(model)
    cores = {c.id for c in wires.values() if is_core(model, c.id)}
    found = []
    for function, item, other, record in ends(model):
        gender = function_gender(model, function)
        if record not in wires or gender is None or record in cores:
            continue
        for unit in crossed_units(model, item, other):
            if function not in boundary_of[unit]:
                continue
            message = (
                f"a conductor lands directly on {ref(function)}, the "
                f"{gender.name.lower()} boundary connector of "
                f"{ref(unit)}; end a cable's cores at the connector's pins, with no mate"
            )
            subjects = (unit, function, record)
            found.append(finding(CONNECTOR_WIRED_WITHOUT_MATE, subjects, message))
    return found


def _unused_contradicted(model: Model) -> list[Finding]:
    owners_of = boundary_owners(model)
    wired = {function for function, *_ in ends(model)}
    found = []
    for unused in (u for u in unused_boundaries(model).values() if carried_unit(model, u) is None):  # a carrier's: `_carrier_unused`
        function = unused.function
        owners = list(owners_of.get(function, ()))
        if not owners:
            if function in wired:
                message = f"UnusedBoundary names {ref(function)}, which is wired, so not unused"
                found.append(finding(UNUSED_CONTRADICTED, (function,), message))
            continue
        for unit in declared_owners(model, unused, owners):
            if not crosses_out_of(model, unit, function):
                continue
            message = f"UnusedBoundary names {ref(function)}, which is connected across {ref(unit)} it is a boundary of"
            found.append(finding(UNUSED_CONTRADICTED, (unit, function), message))
    return found


def _carrier_unused(model: Model) -> list[Finding]:
    """A carrier's `d.unused` point must be a boundary point of a nested unit that nothing wires across (R1761, R1762)."""
    owners_of = boundary_owners(model)
    found = []
    for unused in unused_boundaries(model).values():
        inner, function = carried_unit(model, unused), unused.function
        if inner is None:
            continue
        owners = owners_of.get(function, ())
        if not owners:
            message = f"d.unused names {ref(function)}, which is no boundary point of {ref(inner)}"
            found.append(finding(UNUSED_NOT_BOUNDARY, (inner, function), message))
        elif any(crosses_out_of(model, unit, function) for unit in owners):
            message = f"d.unused names {ref(function)}, which is wired across {ref(inner)}, so not unused"
            found.append(finding(UNUSED_POINT_WIRED, (inner, function), message))
    return found


def _unused_ports_wired(model: Model) -> list[Finding]:
    """A port named in `d.unused` that a conductor, join or mate lands on is contradicted (R1764, R1766)."""
    used = wired_ports(model) | mated_ports(model)
    return [
        finding(UNUSED_POINT_WIRED, (record.port,), f"d.unused names {ref(ports(model)[record.port])}, which is wired, so not unused")
        for record in unused_ports(model).values()
        if record.port in used
    ]


def _boundary_membership(model: Model) -> list[Finding]:
    subtree_of = unit_index(model).subtree_of
    found = []
    for record in boundaries(model).values():
        function = functions(model)[record.function]
        unit = boundary_unit(model, record.id)
        if declared_unit(items(model)[function.item]) not in subtree_of[unit]:
            message = f"boundary function {ref(function)}'s item does not belong to {ref(unit)}'s subtree"
            found.append(finding(BOUNDARY_NOT_IN_UNIT, (unit, record.function), message))
    return found


def check_units(model: Model) -> tuple[Finding, ...]:
    """Check every unit's boundary and every mate's kind; `UNIT_CYCLE` is `check_structure`'s.

    `ERROR`: the boundary codes `BOUNDARY_UNCONNECTED`, `UNIT_BOUNDARY_BYPASSED`,
    `BOUNDARY_NOT_IN_UNIT`, `MATE_NOT_CONNECTOR`, `UNUSED_NOT_BOUNDARY` and `UNUSED_POINT_WIRED`; the others `WARNING`. Sorted by code.
    """
    return ordered(
        [
            *_boundary_unconnected(model),
            *_net_across_unit_boundary(model),
            *_unit_boundary_bypassed(model),
            *_mate_port_mismatch(model),
            *_mate_not_connector(model),
            *_connector_wired_without_mate(model),
            *_unused_contradicted(model),
            *_carrier_unused(model),
            *_unused_ports_wired(model),
            *_boundary_membership(model),
        ]
    )
