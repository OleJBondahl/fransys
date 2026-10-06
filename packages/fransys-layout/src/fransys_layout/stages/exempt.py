"""Which placed ports of a unit's boundary draw nothing (layout-0080).

One definition of "this port's net leaves the unit", read by the member check and by the star
markers alike (`exempt`, a `(port, drawing_set)` set).
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .lookups import nets_from_pairs

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_model.kernel import Id

    from .references.types import Seated
    from .types import Connection, FunctionSpec, Handle, NetGroup, PagePlan


@dataclass(frozen=True)
class ExemptInputs:
    """What `boundary_exempt` reads of the run; `seats` are planned (S10) or placed positions."""

    connections: tuple[Connection, ...]
    net_groups: tuple[NetGroup, ...]
    functions: tuple[FunctionSpec, ...]
    plans: tuple[PagePlan, ...]
    seats: tuple[Seated, ...]


@dataclass(frozen=True)
class UnitNesting:
    """How the units nest: `inside` maps a unit to itself and its enclosers; `nested` the nested."""

    inside: Mapping[Handle, frozenset[Handle]]
    nested: frozenset[Handle | None]


def _neighbours(
    connections: tuple[Connection, ...], net_groups: tuple[NetGroup, ...]
) -> tuple[dict[Id[Any], Id[Any]], dict[Id[Any], set[Id[Any]]], dict[Id[Any], set[Id[Any]]]]:
    """Each port's function, its net-mates by conductor or group, and its whole net's ports."""
    owner: dict[Id[Any], Id[Any]] = {}
    mates: dict[Id[Any], set[Id[Any]]] = defaultdict(set)
    for one in connections:
        for end, other in ((one.a, one.b), (one.b, one.a)):
            owner[end.port] = end.function
            mates[end.port].add(other.port)
    for group in net_groups:
        for ref in group.ports:
            owner[ref.port] = ref.function
            mates[ref.port].update(r.port for r in group.ports if r.port != ref.port)
    net: dict[Id[Any], set[Id[Any]]] = {}
    joined = nets_from_pairs(((port, mate) for port in owner for mate in mates[port]), owner)
    for ports in joined.groups().values():
        seen = set(ports)
        net.update(dict.fromkeys(ports, seen))
    return owner, mates, net


def open_ends(functions: tuple[FunctionSpec, ...], edges: frozenset[Id[Any]]) -> frozenset[Id[Any]]:
    """The drawn functions (pin views included) of boundary `edges`, whose outside is open (U2)."""
    return frozenset(
        spec.function for spec in functions if (spec.pin_function or spec.function) in edges
    )


def boundary_exempt(inputs: ExemptInputs, nesting: UnitNesting) -> frozenset[tuple[Id[Any], int]]:
    """`(port, drawing_set)` of each placed port with no marker and no cover (D9, I2a)."""
    inside = nesting.inside
    owner, mates, net = _neighbours(inputs.connections, inputs.net_groups)
    unit_of = {spec.function: spec.unit for spec in inputs.functions}
    set_unit = {plan.drawing_set: plan.unit for plan in inputs.plans}
    black_boxes = {
        one.function for one in inputs.seats if unit_of[one.function] != set_unit[one.drawing_set]
    }
    ports_of = defaultdict(list)
    for port, function in owner.items():
        ports_of[function].append(port)

    def leaves(mate: Id[Any], unit: Id[Any] | None) -> bool:
        """Whether the port `mate` lies outside `unit` (not in it, nor in a unit nested in it)."""
        return unit not in inside.get(unit_of[owner[mate]], ())

    found = set()
    for one in inputs.seats:
        unit = unit_of[one.function]
        nested = unit in nesting.nested
        for port in ports_of.get(one.function, ()):
            if unit != set_unit[one.drawing_set]:  # the black box, in the parent's set
                # a top-level unit's black box stays exempt whatever its net (its stubs: Part 2)
                exempt = not nested or not any(leaves(mate, unit) for mate in net[port])
            else:  # the unit's own set: a nested unit's pin whose every conductor leaves it
                exempt = (
                    nested
                    and one.function in black_boxes
                    and all(leaves(mate, unit) for mate in mates[port])
                )
            if exempt:
                found.add((port, one.drawing_set))
    return frozenset(found)
