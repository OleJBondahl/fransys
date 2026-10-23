"""The device chains of a block: which devices chain and in what order (LC2, LC3, layout-0215).

A chain is two or more devices of one block where each wire of a member runs alone to a port of
a neighbouring member, at most two neighbours each. A member's connectors stay whole for its box.
"""

from collections import defaultdict
lazy from collections.abc import Sequence
lazy from collections.abc import Set as AbstractSet

from fransys_model.derive.chain_graph import (
    chain_row,
    closed,
    components,
    device_graph,
    ordered,
    partners,
    several_views,
)
from fransys_model.derive.facts.units import boundary, units
from fransys_model.derive.order_kit import chains_in_order
from fransys_model.derive.rows_device_chains import ChainCandidate, DeviceChains
from fransys_model.vocab.tables import mates
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Item, Port

__all__ = ["device_chains"]


def device_chains(
    model: Model,
    candidates: Sequence[ChainCandidate],
    wires: Sequence[tuple[Id[Port], Id[Port]]],
    netted: AbstractSet[Id[Port]],
    wired: AbstractSet[Id[Port]],
) -> DeviceChains:
    """Every device chain over `candidates` (function level, before pin views), in LC3 order.

    A mated function, or a unit's boundary function, keeps its device out of every chain, and so
    does a device with a function that is neither boxed nor a connector. `wires` are the kept
    conductors' port pairs, `netted` the ports of net groups, `wired` the engine's wired ports.
    """
    kept = {f for unit in units(model) for f in boundary(model, unit)}
    kept |= {f for mate in mates(model).values() for f in (mate.a, mate.b)}
    apart = {c.item for c in candidates if c.function in kept or not (c.boxed or c.connector)}
    items: dict[Id[Item], list[ChainCandidate]] = defaultdict(list)
    for c in candidates:
        if c.item not in apart:
            items[c.item].append(c)
    owner = {p: c.item for c in candidates for p in c.ports}
    partner = partners(wires, frozenset(netted))
    links = (partner, owner)
    reached = frozenset({*(p for w in wires for p in w), *netted, *wired})
    graph = closed(device_graph(items, links, reached), items)
    found = [
        chain_row(ordered(members, graph, items), graph, items, links)
        for members in components(graph)
        if len(members) > 1 and any(several_views(items[m]) for m in members)
    ]
    return DeviceChains(chains=chains_in_order(found))
