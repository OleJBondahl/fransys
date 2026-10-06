"""What a physical net is on the drawing: supply, ground, protective earth or none (model-0117)."""

from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, digest_cached
from fransys_model.vocab import ConductorKind, Current, Item, Net, NetClass, Port, PowerKind
from fransys_model.vocab.closure import net_of, physical_nets
from fransys_model.vocab.potentials import pe_firsts, physical_potentials
from fransys_model.vocab.tables import conductors, items, nets, supply_of_potential

from .indexes import build_indexes
from .lookups import item_of_port, terminal_items

_WIRE_PORTS = 2  # a physical net of this many ports is one wire, not a rail (V3)


def _potential_kind(model: Model, potential: str) -> PowerKind:
    """A DC rail's kind by `max_v`: 0 V ground, else supply (A6); an AC or unsupplied one `NONE`."""
    supply = supply_of_potential(model, potential)
    if supply is None or supply.current is not Current.DC:
        return PowerKind.NONE
    return PowerKind.GROUND if supply.rails[potential].max_v == 0 else PowerKind.SUPPLY


@digest_cached(DIGEST_CACHE_SIZE)
def _kinds(model: Model) -> frozendict[Id[Port], PowerKind]:
    """Each net's kind by first port: `PE`, else its potential's, none for two ports (V3)."""
    earth = pe_firsts(model)
    kinds: dict[Id[Port], PowerKind] = {}
    for physical in physical_nets(model):
        first = physical.ports[0]
        potentials = tuple(physical_potentials(model, physical))
        if first in earth:
            kinds[first] = PowerKind.PE
        elif len(potentials) == 1 and len(physical.ports) != _WIRE_PORTS:
            kinds[first] = _potential_kind(model, potentials[0])
    return frozendict(kinds)


def port_power_kind(model: Model, port: Id[Port]) -> PowerKind:
    """The `PowerKind` of the physical net of `port`; `NONE` when `port` is not in `model`.

    A load pin wired to a 24 V terminal gets the kind of that net though no `Net` lists it.
    Cost: O(1) once per model digest, like `port_rails`.
    """
    physical = net_of(model, port)
    return (
        PowerKind.NONE if physical is None else _kinds(model).get(physical.ports[0], PowerKind.NONE)
    )


def power_kind(model: Model, net: Id[Net]) -> PowerKind:
    """The `PowerKind` of declared `net`, read from its physical net, never from its name.

    A net of class `PE` is `PE`, supplied or not. Otherwise the physical net's one potential is
    looked up in the supplies: a DC rail above or below 0 V is `SUPPLY`, a DC rail at 0 V is
    `GROUND`. An AC rail, a potential in no supply, no potential, or two potentials on one
    physical net are `NONE`, as is a net whose ports fall in physical nets of different kinds.
    A physical net of exactly two ports, bridges and links counted, is `NONE` whatever its
    potential: a wire, not a rail; it keeps the potential.
    A DC supply that declares no 0 V rail leaves its 0 V net `NONE`: declare it.

    Raises:
        KeyError: `net` is not a declared `Net` of `model`.
    """
    declared = nets(model)[net]
    if declared.net_class is NetClass.PE:
        return PowerKind.PE
    kinds = {port_power_kind(model, port) for port in declared.ports}
    return kinds.pop() if len(kinds) == 1 else PowerKind.NONE


def power_text(model: Model, net: Id[Net]) -> str | None:
    """The text a power symbol of declared `net` prints, or `None` when it prints none.

    Only `SUPPLY` prints: `Net.name`, else `Net.potential` (which carries the sign of a negative
    rail, `-15V`). `GROUND`, `PE` and `NONE` print none.
    """
    if power_kind(model, net) is not PowerKind.SUPPLY:
        return None
    declared = nets(model)[net]
    return declared.name if declared.name is not None else declared.potential


@digest_cached(DIGEST_CACHE_SIZE)
def _texts(model: Model) -> frozendict[Id[Port], str | None]:
    """Each power physical net's text by its first port: the first declared net's, by net id."""
    texts: dict[Id[Port], str | None] = {}
    for net in sorted(nets(model).values(), key=lambda one: one.id):
        if power_kind(model, net.id) is PowerKind.NONE:
            continue
        for port in net.ports:
            if (physical := net_of(model, port)) is not None:
                texts.setdefault(physical.ports[0], power_text(model, net.id))
    return frozendict(texts)


def port_power_text(model: Model, port: Id[Port]) -> str | None:
    """The text the power symbol at `port` prints: `power_text` of its physical net, else `None`.

    A load pin wired to a 24 V terminal prints that net's text. Cost: O(1) once per model digest.
    """
    physical = net_of(model, port)
    return None if physical is None else _texts(model).get(physical.ports[0])


@digest_cached(DIGEST_CACHE_SIZE)
def _bridged(model: Model) -> frozenset[Id[Item]]:
    """Terminals a `JUMPER` or `RAIL` conductor joins to another terminal of their strip."""
    terminals = terminal_items(model)
    found: set[Id[Item]] = set()
    for conductor in conductors(model).values():
        if conductor.kind not in (ConductorKind.JUMPER, ConductorKind.RAIL):
            continue
        a, b = item_of_port(model, conductor.a), item_of_port(model, conductor.b)
        if a != b and {a, b} <= terminals and items(model)[a].parent == items(model)[b].parent:
            found |= {a, b}
    return frozenset(found)


def is_rail_terminal(model: Model, terminal: Id[Item]) -> bool:
    """Whether `terminal` is a rail terminal: on a DC rail or a PE net, bridged within its strip.

    A rail terminal draws no symbol: its pins show the rail's power symbol. An AC rail,
    an unbridged terminal and any item that is not a terminal are `False`.
    """
    if terminal not in _bridged(model):
        return False
    idx = build_indexes(model)
    return any(
        port_power_kind(model, port) is not PowerKind.NONE
        for function in idx.functions_by_item.get(terminal, ())
        for port in idx.ports_by_function.get(function, ())
    )
