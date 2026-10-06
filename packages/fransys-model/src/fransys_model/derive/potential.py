"""A pin's potential rank and current, read from the supply's declared facts (V11, model-0121)."""

from decimal import Decimal

from fransys_model.derive.indexes import build_indexes
from fransys_model.kernel import DIGEST_CACHE_SIZE, digest_cached
from fransys_model.vocab.closure import net_of, port_rails
from fransys_model.vocab.enums import Current, NetClass
from fransys_model.vocab.tables import nets, supply_systems
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Port
lazy from fransys_model.vocab.supply_system import Rail

_PE_KEY = (5, Decimal(0))


def _order_key(current: Current, rail: Rail) -> tuple[int, Decimal]:
    """AC by phase, DC above 0 V high first, AC at 0 V, DC at 0 V, DC below 0 V high first."""
    if current is Current.AC and rail.phase is not None:
        return (0, Decimal(rail.phase))
    if rail.max_v > 0:
        return (1, -rail.max_v)
    if current is Current.AC:
        return (2, Decimal(0))
    return (3, Decimal(0)) if rail.max_v == 0 else (4, -rail.max_v)


@digest_cached(DIGEST_CACHE_SIZE)
def _ranked(model: Model) -> frozendict[str, tuple[int, Current | None]]:
    """Each declared potential's rank and current; equal facts tie by potential text, PE is last."""
    found: dict[str, tuple[tuple[int, Decimal], Current | None]] = {}
    for supply in supply_systems(model).values():
        for potential, rail in supply.rails.items():
            found.setdefault(potential, (_order_key(supply.current, rail), supply.current))
    for net in nets(model).values():
        if net.net_class is NetClass.PE and net.potential is not None:
            found[net.potential] = (_PE_KEY, None)
    order = sorted(found, key=lambda potential: (found[potential][0], potential))
    return frozendict({p: (index, found[p][1]) for index, p in enumerate(order)})


@digest_cached(DIGEST_CACHE_SIZE)
def _earthed(model: Model) -> frozendict[Id[Port], str]:
    """Each port on the physical net of a PE net, with that net's potential (earth is no rail)."""
    found: dict[Id[Port], str] = {}
    for net in nets(model).values():
        if net.net_class is NetClass.PE and net.potential is not None:
            for port in net.ports:
                physical = net_of(model, port)
                found.update(dict.fromkeys(physical.ports, net.potential) if physical else {})
    return frozendict(found)


def _carried(model: Model, port: Id[Port]) -> str | None:
    """The ranked potential `port` carries: its own net's, else the closure's, else earth's."""
    ranked = _ranked(model)
    own = {nets(model)[net].potential for net in build_indexes(model).nets_by_port.get(port, ())}
    reached = {*port_rails(model, port), _earthed(model).get(port)}
    for pick in (own, reached):
        found = [p for p in pick if p is not None and p in ranked]
        if found:
            return min(found, key=lambda potential: ranked[potential][0])
    return None


def port_potential_rank(model: Model, port: Id[Port]) -> int | None:
    """The rank of the potential `port` carries in service: smaller is drawn higher up, else `None`.

    The order comes from the supply's declared facts, never from a rail's name: AC rails with a
    phase, by phase; DC rails above 0 V, highest first; the AC rail at 0 V; the DC rail at 0 V;
    DC rails below 0 V, highest first; protective earth last. Equal facts tie by potential
    text, since declaration order is no model fact (models differing only in it are equal).
    A port takes its own declared net's potential, else what the rail closure reaches through
    conductors, mates, conductive and switched links (`port_rails`), so a pin behind a contact
    keeps its rank. Reached from two rails (a changeover between two sources), it takes the lower
    rank. A net potential that no supply declares gives `None`. Power-symbol eligibility is a
    separate question that keeps the physical net.
    """
    potential = _carried(model, port)
    return None if potential is None else _ranked(model)[potential][0]


def port_potential_current(model: Model, port: Id[Port]) -> Current | None:
    """The current, AC or DC, of the supply behind `port_potential_rank`'s potential.

    `None` when the port has no rank, and for protective earth, which belongs to no supply.
    """
    potential = _carried(model, port)
    return None if potential is None else _ranked(model)[potential][1]
