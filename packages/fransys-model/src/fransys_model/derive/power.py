"""What a physical net is on the drawing: supply, ground, protective earth or none (model-0117)."""

from fransys_model.derive.facts.closure import net_of, physical_nets
from fransys_model.derive.facts.potentials import pe_firsts, physical_potentials
from fransys_model.derive.facts.protected import protected_by
from fransys_model.derive.facts.unit_index import item_unit
from fransys_model.elecdef import Current
from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, digest_cached
from fransys_model.vocab import Item, Net, Port, PowerKind
from fransys_model.vocab.tables import nets, rail_groups, supply_of_potential

from .facts.net_facts import net_potential
from .lookups import item_of_port
from .order import NaturalKey, natural_key
from .tag_text import item_tag_text

_WIRE_PORTS = 2  # a physical net of this many ports is one wire, not a rail


def _potential_kind(model: Model, potential: str) -> PowerKind:
    """A DC rail's kind by `max_v`: 0 V ground, else supply; an AC or unsupplied one `NONE`."""
    supply = supply_of_potential(model, potential)
    if supply is None or supply.current is not Current.DC:
        return PowerKind.NONE
    return PowerKind.GROUND if supply.rails[potential].max_v == 0 else PowerKind.SUPPLY


@digest_cached(DIGEST_CACHE_SIZE)
def _kinds(model: Model) -> frozendict[Id[Port], PowerKind]:
    """Each net's kind by first port: none for two ports, else `PE`, else its potential's."""
    earth = pe_firsts(model)
    kinds: dict[Id[Port], PowerKind] = {}
    for physical in physical_nets(model):
        first = physical.ports[0]
        potentials = tuple(physical_potentials(model, physical))
        link = first in earth and len({item_of_port(model, p) for p in physical.ports}) == 1  # a PE terminal's two sides: no wire
        if len(physical.ports) == _WIRE_PORTS and not link:
            continue
        if first in earth:
            kinds[first] = PowerKind.PE
        elif len(potentials) == 1:
            kinds[first] = _potential_kind(model, potentials[0])
    return frozendict(kinds)


def port_power_kind(model: Model, port: Id[Port]) -> PowerKind:
    """The `PowerKind` of the physical net of `port`; `NONE` when `port` is not in `model`.

    A load pin wired to a 24 V terminal gets the kind of that net though no `Net` lists it.
    Cost: O(1) once per model digest, like `port_rails`.
    """
    physical = net_of(model, port)
    return PowerKind.NONE if physical is None else _kinds(model).get(physical.ports[0], PowerKind.NONE)


def power_kind(model: Model, net: Id[Net]) -> PowerKind:
    """The `PowerKind` of declared `net`, read from its physical net, never from its name.

    A physical net holding a net of class `PE` is `PE`, supplied or not. Otherwise its one potential is
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
    kinds = {port_power_kind(model, port) for port in declared.ports}
    return kinds.pop() if len(kinds) == 1 else PowerKind.NONE


def power_text(model: Model, net: Id[Net]) -> str | None:
    """The text a power symbol of declared `net` prints, or `None` when it prints none.

    Only `SUPPLY` prints: `Net.name`, else `Net.potential` (which carries the sign of a negative
    rail, `-15V`). A net behind a protective device adds the tag of the nearest one, `24V -F2`
    (`protected_by`, G08-POWER). `GROUND`, `PE` and `NONE` print none.
    """
    if power_kind(model, net) is not PowerKind.SUPPLY:
        return None
    declared = nets(model)[net]
    name = declared.name if declared.name is not None else net_potential(model, net)
    physical = net_of(model, declared.ports[0])
    device = None if name is None or physical is None else protected_by(model).get(physical.ports[0])
    return name if device is None else f"{name} {item_tag_text(model, device, unit=item_unit(model, device))}"


def _text_order(model: Model, net: Net) -> tuple[NaturalKey, Id[Net]]:
    """First-wins order of declared nets: printed name or potential, naturally, then id."""
    return natural_key(net.name or net_potential(model, net.id) or ""), net.id


@digest_cached(DIGEST_CACHE_SIZE)
def _texts(model: Model) -> frozendict[Id[Port], str | None]:
    """Each power physical net's text by its first port: the first declared net's, by net id."""
    texts: dict[Id[Port], str | None] = {}
    for net in sorted(nets(model).values(), key=lambda n: _text_order(model, n)):
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
def _flagged(model: Model) -> frozenset[Id[Item]]:
    """The terminals of every declared `RailGroup`."""
    return frozenset(terminal for group in rail_groups(model).values() for terminal in group.terminals)


def is_rail_terminal(model: Model, terminal: Id[Item]) -> bool:
    """Whether `terminal` is a rail terminal: true exactly when its group carries the flag.

    A rail terminal draws no symbol: its pins show the rail's power symbol. An unflagged
    terminal, bridged or not, and any item that is not a terminal are `False`.
    """
    return terminal in _flagged(model)
