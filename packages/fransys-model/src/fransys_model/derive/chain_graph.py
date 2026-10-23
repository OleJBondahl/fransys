"""The device graph of `device_chains`: who is wired alone to whom, the parts, the order."""

from collections import defaultdict
from itertools import pairwise
lazy from collections.abc import Mapping, Sequence

from fransys_model.derive.order_kit import candidates_in_order, first_device
from fransys_model.derive.rows_device_chains import ChainCandidate, ChainHop, ChainPin, ChainRow
lazy from fransys_model.kernel import Id, canonical
lazy from fransys_model.vocab.core import Item, Port

type Graph = dict[Id[Item], frozenset[Id[Item]]]
type Items = Mapping[Id[Item], Sequence[ChainCandidate]]
type Links = tuple[Mapping[Id[Port], Id[Port]], Mapping[Id[Port], Id[Item]]]

_TWO = 2  # a member has one device above and one below


def partners(
    wires: Sequence[tuple[Id[Port], Id[Port]]], netted: frozenset[Id[Port]]
) -> dict[Id[Port], Id[Port]]:
    """Each port whose one conductor ends at a port with one, no net group, to that port."""
    count: dict[Id[Port], int] = defaultdict(int)
    for a, b in wires:
        count[a] += 1
        count[b] += 1
    found = {}
    for a, b in wires:
        if count[a] == 1 and count[b] == 1 and a not in netted and b not in netted:
            found[a], found[b] = b, a
    return found


def block(group: Sequence[ChainCandidate]) -> object | None:
    """The one block of a device that may join a chain, else `None`."""
    places = {(c.group_path, c.in_unit, c.location_path) for c in group}
    return next(iter(places)) if all(c.plain for c in group) and len(places) == 1 else None


def _neighbours(
    group: Sequence[ChainCandidate], links: Links, wired: frozenset[Id[Port]]
) -> frozenset[Id[Item]] | None:
    """The devices `group`'s wired ports reach, each wire alone; `None` when one is not alone."""
    partner, owner = links
    found: set[Id[Item]] = set()
    for port in (p for c in group for p in c.ports if p in wired):
        far = partner.get(port)
        if far is None or far not in owner:
            return None
        found.add(owner[far])
    return frozenset(found)


def device_graph(items: Items, links: Links, wired: frozenset[Id[Port]]) -> Graph:
    """Each device that may chain, to its one or two neighbouring devices (LC2)."""
    graph: Graph = {}
    for item, group in items.items():
        near = _neighbours(group, links, wired)
        if near and len(near) <= _TWO and item not in near and block(group) is not None:
            graph[item] = near
    return graph


def closed(graph: Graph, items: Items) -> Graph:
    """`graph` less each device wired to one outside it or in another block (LC5), until none is."""
    kept: Graph = dict(graph)
    while True:
        out = {
            item
            for item, near in kept.items()
            if any(n not in kept or block(items[n]) != block(items[item]) for n in near)
        }
        if not out:
            return kept
        kept = {item: near for item, near in kept.items() if item not in out}


def components(graph: Graph) -> list[frozenset[Id[Item]]]:
    """The connected parts of `graph`, each a path or a ring, in handle order."""
    seen: set[Id[Item]] = set()
    found = []
    for start in canonical(graph):
        if start in seen:
            continue
        part, todo = {start}, [start]
        while todo:
            ahead = graph[todo.pop()] - part
            part |= ahead
            todo.extend(canonical(ahead))
        seen |= part
        found.append(frozenset(part))
    return found


def several_views(group: Sequence[ChainCandidate]) -> bool:
    """Whether a device spreads over views without LC2: a connector beside another function."""
    return len(group) > 1 and any(c.connector for c in group)


def ordered(members: frozenset[Id[Item]], graph: Graph, items: Items) -> tuple[Id[Item], ...]:
    """LC3: an open chain from its end that sorts first; a ring from its first, toward its first."""
    ends = [m for m in members if len(graph[m]) == 1]
    ranks = {m: min(c.rank for c in items[m]) for m in members}
    order = [first_device(ends or members, ranks)]
    while len(order) < len(members):
        ahead = [n for n in graph[order[-1]] if n not in order]
        order.append(first_device(ahead, ranks))
    return tuple(order)


def _hop(upper: Id[Item], lower: Id[Item], items: Items, links: Links) -> ChainHop:
    """The wires from `upper` to `lower`, in the upper device's function and port order."""
    partner, owner = links
    pins = [
        ChainPin(fed=partner[p], feeder=p)
        for c in candidates_in_order(items[upper])
        for p in c.ports
        if p in partner and owner.get(partner[p]) == lower
    ]
    return ChainHop(fed=lower, feeder=upper, pins=tuple(pins))


def chain_row(order: tuple[Id[Item], ...], graph: Graph, items: Items, links: Links) -> ChainRow:
    """The chain of `order`, its hops top to bottom; a ring's last-to-first hop is `closing`."""
    hops = tuple(_hop(a, b, items, links) for a, b in pairwise(order))
    ring = len(order) > _TWO and order[0] in graph[order[-1]]
    closing = _hop(order[-1], order[0], items, links) if ring else None
    return ChainRow(members=order, hops=hops, closing=closing)
