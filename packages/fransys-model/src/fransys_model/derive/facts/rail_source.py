"""Where a rail's potential comes from: the declaring unit of its supply, when one cabinet is fed that potential by several (R2589)."""

from fransys_model.derive.facts.closure import _adjacency, _rail_sources, net_of, rail_reach
from fransys_model.derive.facts.net_facts import net_potential
from fransys_model.derive.facts.supply_sources import supplies_by_potential
from fransys_model.derive.facts.unit_index import item_unit
from fransys_model.derive.indexes import build_indexes
from fransys_model.derive.lookups import item_of_port
from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, digest_cached
lazy from fransys_model.vocab import Port, Unit
lazy from fransys_model.vocab.supply_system import SupplySystem

__all__ = ["rail_source_unit"]


def _cabinet(model: Model, port: Id[Port]) -> Id[Unit] | None:
    """The cabinet of `port`: the unit of its item."""
    return item_unit(model, item_of_port(model, port))


def _seeds(model: Model, supply: SupplySystem, potential: str) -> frozenset[Id[Port]]:
    """The physical nets of `supply`'s pins that carry `potential`."""
    held = build_indexes(model).nets_by_port
    own: set[Id[Port]] = set()
    for pin in supply.pins:
        if any(net_potential(model, net) == potential for net in held.get(pin, ())):
            physical = net_of(model, pin)
            own.update(physical.ports if physical else (pin,))
    return frozenset(own)


def _sources_of(model: Model, potential: str, supplies: tuple[SupplySystem, ...]) -> dict[frozenset[Id[Port]], Id[Unit]]:
    """The unbonded sources of `potential`, by their own ports: two supplies on one physical net are one source."""
    found: dict[frozenset[Id[Port]], Id[Unit]] = {}
    for supply in supplies:
        if supply.pins and (own := _seeds(model, supply, potential)) and (unit := _cabinet(model, supply.pins[0])) is not None:
            found.setdefault(own, unit)
    return found


def _qualified(model: Model, reach: dict[frozenset[Id[Port]], frozenset[Id[Port]]]) -> dict[Id[Port], frozenset[Id[Port]]]:
    """Each port that exactly one source reaches, in a cabinet that two or more reach, with that source's own ports."""
    fed: dict[Id[Unit] | None, set[frozenset[Id[Port]]]] = {}
    sole: dict[Id[Port], list[frozenset[Id[Port]]]] = {}
    for own, ports in reach.items():
        for port in ports:
            fed.setdefault(_cabinet(model, port), set()).add(own)
            sole.setdefault(port, []).append(own)
    return {port: owns[0] for port, owns in sole.items() if len(owns) == 1 and len(fed[_cabinet(model, port)]) > 1}


@digest_cached(DIGEST_CACHE_SIZE)
def _sources(model: Model) -> frozendict[Id[Port], Id[Unit]]:
    """Each port's declaring unit where its cabinet is fed one potential by two or more unbonded supplies."""
    shared = {potential: supplies for potential, supplies in supplies_by_potential(model).items() if len(supplies) > 1}
    found: dict[Id[Port], Id[Unit]] = {}
    declared = frozenset(port for start in _rail_sources(model).values() for port in start) if shared else frozenset()
    adjacent = _adjacency(model) if shared else {}
    for potential, supplies in shared.items():
        sources = _sources_of(model, potential, supplies)
        if len(sources) > 1:
            for port, own in _qualified(model, {own: rail_reach(adjacent, declared, own) for own in sources}).items():
                found.setdefault(port, sources[own])
    return frozendict(found)


def rail_source_unit(model: Model, port: Id[Port]) -> Id[Unit] | None:
    """The unit declaring the supply `port`'s potential comes from, where its cabinet is fed it by two or more unbonded supplies, else `None`.

    Two supplies are bonded when their pins' physical nets are one. A port that two supplies reach has no one source: `None`.
    The text a power symbol prints (`power_text`) and the join class of a ground symbol both read it, never a printed text.
    Cost: O(1) once per model digest.
    """
    return _sources(model).get(port)
