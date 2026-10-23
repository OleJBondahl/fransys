"""The potentials one physical net carries: the one read, shared by a validator and `power_kind`."""

from fransys_model.derive.facts.closure import PhysicalNet, net_of
from fransys_model.derive.facts.net_facts import is_earth_net, net_potential
from fransys_model.derive.facts.roles import is_pe_port
from fransys_model.kernel import DIGEST_CACHE_SIZE, digest_cached
from fransys_model.vocab.tables import nets, ports
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.connectivity import Net
lazy from fransys_model.vocab.core import Port


@digest_cached(DIGEST_CACHE_SIZE)
def _carried(model: Model) -> frozendict[Id[Port], frozendict[str, tuple[Id[Net], ...]]]:
    """Each physical net's potentials with their declared nets, the net keyed by its first port."""
    found: dict[Id[Port], dict[str, set[Id[Net]]]] = {}
    for net in nets(model).values():
        potential = net_potential(model, net.id)
        if potential is None:
            continue
        for port in net.ports:
            physical = net_of(model, port)
            if physical is not None:
                by_name = found.setdefault(physical.ports[0], {})
                by_name.setdefault(potential, set()).add(net.id)
    return frozendict(
        {
            first: frozendict({name: tuple(sorted(ids)) for name, ids in by_name.items()})
            for first, by_name in found.items()
        }
    )


def physical_potentials(
    model: Model, physical: PhysicalNet
) -> frozendict[str, tuple[Id[Net], ...]]:
    """The potentials the declared nets on `physical` carry, each with its net ids; cached."""
    return frozendict(_carried(model).get(physical.ports[0], {}))


def pe_firsts(model: Model) -> frozenset[Id[Port]]:
    """The first port of each physical net holding a port of an earth net."""
    physical = (
        net_of(model, port)
        for net in nets(model).values()
        if is_earth_net(model, net.id)
        for port in net.ports
    )
    return frozenset(net.ports[0] for net in physical if net is not None)


def on_pe_net(model: Model, port: Id[Port]) -> bool:
    """Whether `port` lies on a physical net holding a port of an earth net."""
    physical = net_of(model, port)
    return physical is not None and physical.ports[0] in pe_firsts(model)


@digest_cached(DIGEST_CACHE_SIZE)
def declared_firsts(model: Model) -> frozenset[Id[Port]]:
    """The first port of each physical net holding a port of any declared net."""
    physical = (net_of(model, port) for net in nets(model).values() for port in net.ports)
    return frozenset(net.ports[0] for net in physical if net is not None)


def on_declared_net(model: Model, port: Id[Port]) -> bool:
    """Whether `port` lies on a physical net holding a port of any declared net."""
    physical = net_of(model, port)
    return physical is not None and physical.ports[0] in declared_firsts(model)


def is_wired(model: Model, port: Id[Port]) -> bool:
    """Whether `port` shares a physical net with another port."""
    physical = net_of(model, port)
    return physical is not None and len(physical.ports) > 1


@digest_cached(DIGEST_CACHE_SIZE)
def pe_ports_off_pe(model: Model) -> tuple[Id[Port], ...]:
    """The wired PE-role ports whose physical net holds no earth net."""
    return tuple(
        port
        for port in ports(model)
        if is_pe_port(model, port) and is_wired(model, port) and not on_pe_net(model, port)
    )
