"""The protective device nearest in front of each physical net, walked from the supplies' own nets (KI-778, R1976)."""

from typing import TYPE_CHECKING

from fransys_model.derive.facts.closure import link_groups, physical_nets
from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, digest_cached
from fransys_model.vocab.tables import functions, ports, supply_systems

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_model.derive.facts.closure import LinkGroup
    from fransys_model.vocab import Item, Port
    from fransys_model.vocab.roles_types import LinkRole

__all__ = ["protected_by"]


def _roots(first: Mapping[Id[Port], Id[Port]], model: Model, behind: frozenset[Id[Item]]) -> frozenset[Id[Port]]:
    """The nets of the supplies' pins that sit on no protective device: a supply's own net."""
    pins = (pin for supply in supply_systems(model).values() for pin in supply.pins)
    return frozenset(first[pin] for pin in pins if functions(model)[ports(model)[pin].function].item not in behind)


def _protective(role: LinkRole) -> bool:
    return role.protective


def _walk(roots: frozenset[Id[Port]], edges: tuple[tuple[Id[Item], frozenset[Id[Port]]], ...]) -> dict[Id[Port], set[Id[Item]]]:
    """Per net, the devices it was first reached through, one layer of devices at a time from `roots`."""
    seen, layer = set(roots), set(roots)
    nearest: dict[Id[Port], set[Id[Item]]] = {}
    while layer:
        arrived: dict[Id[Port], set[Id[Item]]] = {}
        for item, nets in edges:
            if nets & layer:
                for there in nets - seen:
                    arrived.setdefault(there, set()).add(item)
        seen |= arrived.keys()
        nearest.update(arrived)
        layer = set(arrived)
    return nearest


@digest_cached(DIGEST_CACHE_SIZE)
def protected_by(model: Model) -> frozendict[Id[Port], Id[Item]]:
    """Each physical net behind a protective device, mapped to its nearest device (a tie or a supply's own net: absent).

    The walk starts at the supplies' own nets and crosses one protective link per step, so supply -> F1 -> F2 -> load maps the load to F2.
    """
    groups: tuple[LinkGroup, ...] = tuple(link_groups(model, _protective))
    first = {p: net.ports[0] for net in physical_nets(model) for p in net.ports}
    edges = tuple((g.item, frozenset(first[p] for p in g.ports)) for g in groups)
    found = _walk(_roots(first, model, frozenset(g.item for g in groups)), edges)
    return frozendict({net: next(iter(items)) for net, items in found.items() if len(items) == 1})
