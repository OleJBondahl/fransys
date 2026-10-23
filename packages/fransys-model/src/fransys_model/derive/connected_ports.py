"""The ports the schematic engine counts as connected: `wired` of its read step, as a fact.

A port is connected when a kept connection or net group ends on it, a connection or group with an
undrawn far end strands it, or it is a rail end (model-0325, amended). It is not `port_is_reached`.
"""

lazy from collections.abc import Iterable

from fransys_model.derive.facts.bars import bar_items
from fransys_model.derive.facts.item_predicates import terminal_items
from fransys_model.derive.facts.roles import conductor_role, function_role
from fransys_model.derive.facts.units import (
    boundary,
    crosses_unit,
    enclosing_boards,
    is_sole_unit_root,
    units,
)
from fransys_model.derive.power import is_rail_terminal, port_power_kind
from fransys_model.derive.structure import schematic_functions
from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, digest_cached
from fransys_model.vocab.enums import PowerKind
from fransys_model.vocab.tables import conductors, functions, nets, ports
lazy from fransys_model.vocab.connectivity import Conductor
lazy from fransys_model.vocab.core import Function, Item, Port

__all__ = ["connected_ports"]


def _item(model: Model, port: Id[Port]) -> Id[Item]:
    return functions(model)[ports(model)[port].function].item


def _items(model: Model, conductor: Conductor) -> tuple[Id[Item], Id[Item]]:
    return _item(model, conductor.a), _item(model, conductor.b)


def _on_board(model: Model, items: Iterable[Id[Item]]) -> bool:
    """Whether one opaque board is an ancestor-or-self of every item: its nets are not drawn."""
    common: frozenset[Id[Item]] | None = None
    for item in items:
        boards = frozenset(
            b for b in enclosing_boards(model, item) if not is_sole_unit_root(model, b)
        )
        common = boards if common is None else common & boards
        if not common:
            return False
    return bool(common)


def _undrawn(model: Model, drawn: frozenset[Id[Function]]) -> frozenset[Id[Function]]:
    """The rail terminals and bars of `drawn`: their wires become rail ends."""
    bars, table = bar_items(model), functions(model)
    return frozenset(
        f
        for f in drawn
        if table[f].item in bars
        or (function_role(model, f).terminal and is_rail_terminal(model, table[f].item))
    )


def _live(model: Model, port: Id[Port]) -> bool:
    return port_power_kind(model, port) is not PowerKind.NONE


def _rail_ends(
    model: Model, conductor: Conductor, sets: tuple[frozenset[Id[Function]], ...]
) -> frozenset[Id[Port]] | None:
    """The drawn ends of a rail wire, `None` when the conductor is no rail wire."""
    specs, undrawn, boundary_functions = sets
    strips = terminal_items(model)
    ends = (conductor.a, conductor.b)
    function = [ports(model)[p].function for p in ends]
    pins = {f for f in specs if functions(model)[f].item not in strips}
    if not any(f in undrawn for f in function):
        is_wire = all(f in pins and _live(model, p) for f, p in zip(function, ends, strict=True))
    else:
        is_wire = any(
            f in specs - undrawn and _live(model, p) for f, p in zip(function, ends, strict=True)
        )
    crosses = any(f in boundary_functions for f in function) and crosses_unit(
        model, *(functions(model)[f].item for f in function)
    )
    if not is_wire or crosses:
        return None
    keep = specs - undrawn if any(f in undrawn for f in function) else pins
    return frozenset(p for f, p in zip(function, ends, strict=True) if f in keep)


def _rail_link(model: Model, conductor: Conductor) -> bool:
    """A busbar or rail link with an end on a rail terminal: a join, not a drawn connection."""
    role = conductor_role(model, conductor.id)
    link = role.joins_net and not (role.bridge or role.mount or role.lead)
    return link and any(
        is_rail_terminal(model, _item(model, p)) for p in (conductor.a, conductor.b)
    )


def _wires(model: Model) -> tuple[Conductor, ...]:
    """The conductors a drawing connects: no jumper, no busbar or rail link to a rail terminal."""
    return tuple(
        c
        for c in conductors(model).values()
        if not conductor_role(model, c.id).bridge and not _rail_link(model, c)
    )


def _earth_ends(model: Model, specs: frozenset[Id[Function]]) -> frozenset[Id[Port]]:
    """The PE ports of drawn pins: each takes a stand-in rail end, so it is connected."""
    strips, table = terminal_items(model), functions(model)
    return frozenset(
        p
        for p, record in ports(model).items()
        if record.function in specs
        and table[record.function].item not in strips
        and port_power_kind(model, p) is PowerKind.PE
    )


def _split(
    model: Model, sets: tuple[frozenset[Id[Function]], ...]
) -> tuple[set[Id[Port]], list[Conductor]]:
    """The rail ends (rail wires and PE stand-ins) and the conductors left as connections."""
    rail: set[Id[Port]] = set()
    kept: list[Conductor] = []
    for conductor in _wires(model):
        found = _rail_ends(model, conductor, sets)
        if found is None:
            kept.append(conductor)
        else:
            rail |= found
    return rail | _earth_ends(model, sets[0]), kept


def _group_ends(
    model: Model, undrawn: frozenset[Id[Function]], rail: set[Id[Port]]
) -> set[Id[Port]]:
    """The kept net groups' ports, less removed rail terminals and rail ends; none on a board."""
    found: set[Id[Port]] = set()
    for net in nets(model).values():
        left = [p for p in net.ports if ports(model)[p].function not in undrawn and p not in rail]
        whole = len(left) == len(net.ports)
        held = list(net.ports) if whole else left
        if (whole or len(held) > 1) and not _on_board(model, (_item(model, p) for p in held)):
            found |= set(held)
    return found


@digest_cached(DIGEST_CACHE_SIZE)
def connected_ports(model: Model) -> frozenset[Id[Port]]:
    """Every port a kept connection or net group ends on, a stranded end, or a rail end.

    A connection or net group wholly on one opaque board is not drawn, so its ports are not
    connected by it. A net group loses the ports of removed rail terminals and rail ends first.
    """
    drawn = frozenset(schematic_functions(model))
    undrawn = _undrawn(model, drawn)
    edge = frozenset(f for unit in units(model) for f in boundary(model, unit))
    rail, kept = _split(model, (drawn - (undrawn - edge), undrawn, undrawn & edge))
    wired = {p for c in kept for p in (c.a, c.b) if not _on_board(model, _items(model, c))}
    return frozenset(rail | wired | _group_ends(model, undrawn, rail))
