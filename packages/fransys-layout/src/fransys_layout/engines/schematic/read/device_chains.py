"""LC2, LC3 (layout-0215): the device chains of a block, read once from the functions and wires.

A device chain is two or more devices of one block where each wire of a member runs alone to a
port of a neighbouring member, at most two neighbours each. A member draws no symbol of its own:
each of its functions is box-drawn or a connector. One member at least holds a connector beside
another function, which would otherwise spread over pin views and a box of their own: a series
of symbols, of boxes or of connectors alone stays as it draws today.
"""

from collections import defaultdict
from itertools import pairwise
from typing import TYPE_CHECKING, Any

from fransys_layout.stages import BoxFeed, FedPin
from fransys_layout.stages.types import DeviceChain, Home

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from collections.abc import Set as AbstractSet

    from fransys_layout.stages import Connection, FunctionSpec
    from fransys_layout.stages.types import NetGroup
    from fransys_model.kernel import Id

type Specs = Sequence[FunctionSpec]
type Graph = dict[Id[Any], frozenset[Id[Any]]]
type Items = Mapping[Id[Any], Specs]


def device_chains(
    specs: Specs,
    connections: Sequence[Connection],
    net_groups: Sequence[NetGroup],
    facts: tuple[AbstractSet[Id[Any]], AbstractSet[Id[Any]], AbstractSet[Id[Any]]],
) -> tuple[DeviceChain, ...]:
    """Every device chain over `specs` (function level, before pin views), in LC3 order.

    `facts`: the box-drawn functions, the wired ports (a rail end too) and the functions kept
    apart (mated, or a unit's boundary), which join no chain.
    """
    boxed, wired, kept_apart = facts
    owner = {p.port: spec for spec in specs for p in spec.ports}
    partner, own_wired = _alone(connections, net_groups)
    apart = {
        s.item
        for s in specs
        if s.function in kept_apart or (s.function not in boxed and s.kind != "connector")
    }
    items: dict[Id[Any], list[FunctionSpec]] = defaultdict(list)
    for spec in specs:
        if spec.item not in apart:
            items[spec.item].append(spec)
    graph = _closed(_graph(items, owner, (partner, {*own_wired, *wired})), items)
    found = [
        _chain(_ordered(members, graph, items), graph, items, (owner, partner))
        for members in _components(graph)
        if len(members) > 1 and any(_several_views(items[m]) for m in members)
    ]
    return tuple(sorted(found, key=lambda chain: chain.members))


def _alone(
    connections: Sequence[Connection], net_groups: Sequence[NetGroup]
) -> tuple[dict[Id[Any], Id[Any]], set[Id[Any]]]:
    """Each port whose one conductor ends at a port with one, no net group, to it; and the wired."""
    count: dict[Id[Any], int] = defaultdict(int)
    for c in connections:
        count[c.a.port] += 1
        count[c.b.port] += 1
    for group in net_groups:
        for ref in group.ports:
            count[ref.port] += 2  # a net group's port is never alone
    found = {}
    for c in connections:
        if count[c.a.port] == 1 and count[c.b.port] == 1:
            found[c.a.port], found[c.b.port] = c.b.port, c.a.port
    return found, set(count)


def _block(group: Specs) -> tuple[Any, ...] | None:
    """The one block, unit and location of a device that may join a chain, else `None`."""
    places = {(s.group_path, s.unit, s.location_path) for s in group}
    plain = all(not s.roles.terminal and s.home is Home.HERE for s in group)
    return next(iter(places)) if plain and len(places) == 1 else None


def _neighbours(
    group: Specs,
    owner: Mapping[Id[Any], FunctionSpec],
    links: tuple[Mapping[Id[Any], Id[Any]], set[Id[Any]]],
) -> frozenset[Id[Any]] | None:
    """The devices `group`'s wired ports reach, each wire alone; `None` when one is not alone."""
    partner, wired = links
    found: set[Id[Any]] = set()
    for port in (p.port for spec in group for p in spec.ports if p.port in wired):
        far = partner.get(port)
        if far is None or far not in owner:
            return None
        found.add(owner[far].item)
    return frozenset(found)


def _graph(
    items: Items,
    owner: Mapping[Id[Any], FunctionSpec],
    links: tuple[Mapping[Id[Any], Id[Any]], set[Id[Any]]],
) -> Graph:
    """Each device that may chain, to its one or two neighbouring devices (LC2)."""
    graph: Graph = {}
    for item, group in items.items():
        near = _neighbours(group, owner, links)
        if near and len(near) <= 2 and item not in near and _block(group) is not None:  # noqa: PLR2004 -- a member has one device above and one below
            graph[item] = near
    return graph


def _closed(graph: Graph, items: Items) -> Graph:
    """`graph` less each device wired to one outside it or in another block (LC5), until none is."""
    kept = dict(graph)
    while True:
        out = {
            item
            for item, near in kept.items()
            if any(n not in kept or _block(items[n]) != _block(items[item]) for n in near)
        }
        if not out:
            return kept
        kept = {item: near for item, near in kept.items() if item not in out}


def _components(graph: Graph) -> list[frozenset[Id[Any]]]:
    """The connected parts of `graph`, each a path or a ring, in handle order."""
    seen: set[Id[Any]] = set()
    found = []
    for start in sorted(graph):
        if start in seen:
            continue
        part, todo = {start}, [start]
        while todo:
            ahead = graph[todo.pop()] - part
            part |= ahead
            todo.extend(sorted(ahead))
        seen |= part
        found.append(frozenset(part))
    return found


def _several_views(group: Specs) -> bool:
    """Whether a device spreads over views without LC2: a connector beside another function.

    A connector draws a view per pin, apart from its device's box; a device whose functions are
    all box-drawn is one item box already.
    """
    return len(group) > 1 and any(spec.kind == "connector" for spec in group)


def _rank(items: Items, item: Id[Any]) -> tuple[int, Id[Any]]:
    """LC3's order key of a device: its designation's natural rank, then its handle."""
    return min(spec.designation_order for spec in items[item]), item


def _ordered(members: frozenset[Id[Any]], graph: Graph, items: Items) -> tuple[Id[Any], ...]:
    """LC3: an open chain from its end that sorts first; a ring from its first, toward its first."""
    ends = [m for m in members if len(graph[m]) == 1]
    first = min(ends or members, key=lambda m: _rank(items, m))
    order = [first]
    while len(order) < len(members):
        ahead = [n for n in graph[order[-1]] if n not in order]
        order.append(min(ahead, key=lambda m: _rank(items, m)))
    return tuple(order)


def _hop(
    upper: Id[Any],
    lower: Id[Any],
    items: Items,
    links: tuple[Mapping[Id[Any], FunctionSpec], Mapping[Id[Any], Id[Any]]],
) -> BoxFeed:
    """The wires from `upper` to `lower`, in the upper device's function and port order."""
    owner, partner = links
    pins = [
        FedPin(fed=partner[p.port], feeder=p.port)
        for spec in sorted(items[upper], key=lambda s: s.key)
        for p in spec.ports
        if p.port in partner and owner[partner[p.port]].item == lower
    ]
    return BoxFeed(fed=lower, feeder=upper, ports=tuple(pins))


def _chain(
    order: tuple[Id[Any], ...],
    graph: Graph,
    items: Items,
    links: tuple[Mapping[Id[Any], FunctionSpec], Mapping[Id[Any], Id[Any]]],
) -> DeviceChain:
    """The chain of `order`, its hops top to bottom; a ring's last-to-first hop is `closing`."""
    hops = tuple(_hop(a, b, items, links) for a, b in pairwise(order))
    ring = len(order) > 2 and order[0] in graph[order[-1]]  # noqa: PLR2004 -- two devices are one hop, never a ring
    closing = _hop(order[-1], order[0], items, links) if ring else None
    return DeviceChain(members=order, hops=hops, closing=closing)


def chain_sides(chains: Sequence[DeviceChain]) -> tuple[tuple[Id[Any], ...], tuple[Id[Any], ...]]:
    """LC2: the pins wired to the device above, on top; those wired to the one below, beneath."""
    hops = [
        hop
        for chain in chains
        for hop in (*chain.hops, *([chain.closing] if chain.closing else []))
    ]
    return (
        tuple(sorted(pin.fed for hop in hops for pin in hop.ports)),
        tuple(sorted(pin.feeder for hop in hops for pin in hop.ports)),
    )
