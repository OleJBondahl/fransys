"""Net closure: the physical nets, computed from conductors, links and mates (connectivity.md).

Lives in `vocab` because `validators/connectivity.py` reads it and a layer imports only the
layers to its right; `derive.closure` re-exports it (decision 0019).
"""

import dataclasses
from typing import TYPE_CHECKING, Final, Literal, cast

from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, UnionFind, digest_cached, value

from .contacts import link_state
from .core import Function, Port
from .enums import LinkKind
from .joins import port_joins
from .tables import conductors, functions, internal_links, mates, nets, ports, supply_of_potential

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator, Sequence

    from .core import Item
    from .templates import InternalLink, PortTemplate

# The link kinds each closure joins: a rail also passes a `switched` link (every contact closed)
# and a `protective` one (a fuse or breaker, closed in service); the physical net stops at both.
_PHYSICAL_LINKS: Final = frozenset({LinkKind.CONDUCTIVE})
_RAIL_LINKS: Final = frozenset({LinkKind.CONDUCTIVE, LinkKind.SWITCHED, LinkKind.PROTECTIVE})

# What a rail needs to reach a port: the state each item on its way must be in (CS4). An empty
# condition needs nothing. A condition that names one item in two states can never hold.
type Condition = frozenset[tuple[Id[Item], Literal["rest", "operated"]]]
# The cast: an empty set, whose elements ty infers Unknown.
_ALWAYS: Final[Condition] = cast("Condition", frozenset())


@value
class PhysicalNet:
    """One physical net: a maximal set of ports joined by real connectivity.

    Distinct from `vocab.connectivity.Net`, which is declared intent. `ports` is sorted
    by id, so two closures over the same physical wiring compare equal regardless of
    which port the union-find happened to visit first.

    Attributes:
        ports: The net's ports, sorted by id.
    """

    ports: tuple[Id[Port], ...]


@dataclasses.dataclass(frozen=True, slots=True)
class _Closure:
    """The nets, sorted, and each port's net, for the one digest."""

    nets: tuple[PhysicalNet, ...]
    by_port: frozendict[Id[Port], PhysicalNet]


@dataclasses.dataclass(frozen=True, slots=True)
class LinkGroup:
    """The ports one link of one item ties together, with the item and function it acts in.

    `function` is the function of the first port, the one `link_state` is asked about.
    Package-internal: `derive` does not re-export it.
    """

    link: InternalLink
    item: Id[Item]
    function: Id[Function]
    ports: tuple[Id[Port], ...]


def link_groups(model: Model, kinds: frozenset[LinkKind]) -> Iterator[LinkGroup]:
    """Yield, per item, the ports whose templates a link of one of `kinds` connects.

    The one home of the grouping. The scope is the item, not the function: a link is a part fact.
    Each group is one port of the first template plus the item's ports of the second.
    """
    item_of = {function.id: function.item for function in functions(model).values()}
    by_item_template: dict[tuple[Id[Item], Id[PortTemplate]], list[Id[Port]]] = {}
    by_template: dict[Id[PortTemplate], list[Port]] = {}
    for port in ports(model).values():
        if port.template is not None:
            by_item_template.setdefault((item_of[port.function], port.template), []).append(port.id)
            by_template.setdefault(port.template, []).append(port)
    for link in internal_links(model).values():
        if link.kind not in kinds:
            continue
        for first in by_template.get(link.a, ()):
            item = item_of[first.function]
            others = by_item_template.get((item, link.b), ())
            yield LinkGroup(link, item, first.function, (first.id, *others))


def _join_mates(model: Model, join_all: Callable[[Sequence[Id[Port]]], None]) -> None:
    """Join each header join's two ports, then, per port name, the ports of two mated functions."""
    for pair in port_joins(model):
        join_all(pair)
    by_function: dict[Id[Function], list[Port]] = {}
    for port in ports(model).values():
        by_function.setdefault(port.function, []).append(port)
    for mate in mates(model).values():
        by_name: dict[str, list[Id[Port]]] = {}
        for port in (*by_function.get(mate.a, ()), *by_function.get(mate.b, ())):
            by_name.setdefault(port.name, []).append(port.id)
        for named in by_name.values():
            join_all(named)


def _nets_from(sets: UnionFind[Id[Port]]) -> tuple[PhysicalNet, ...]:
    """The nets of `sets`: each net's ports sorted, the nets sorted by their `ports`."""
    return tuple(
        sorted(
            (PhysicalNet(ports=tuple(sorted(group))) for group in sets.groups().values()),
            key=lambda net: net.ports,
        )
    )


@digest_cached(DIGEST_CACHE_SIZE)
def _closure(model: Model) -> _Closure:
    sets = UnionFind(ports(model))
    for conductor in conductors(model).values():
        sets.union(conductor.a, conductor.b)
    for group in link_groups(model, _PHYSICAL_LINKS):
        sets.union_all(group.ports)
    _join_mates(model, sets.union_all)
    joined = _nets_from(sets)
    return _Closure(
        nets=joined, by_port=frozendict({port: net for net in joined for port in net.ports})
    )


def physical_nets(model: Model) -> tuple[PhysicalNet, ...]:
    """Union-find `model`'s ports into physical nets.

    Ports join through `Conductor`s, `conductive` `InternalLink`s (per item, through each port's
    `PortTemplate`) and `Mate`s (equal port names). `switched` links never join, so a relay's coil
    and contact stay separate nets. A port with no connectivity or no template is its own singleton
    `PhysicalNet`. Sorted by each net's `ports`, so record order never matters; cached on
    `model.digest`.

    Args:
        model: The model to read.

    Returns:
        Every physical net, sorted by its own `ports` tuple.
    """
    return _closure(model).nets


def net_of(model: Model, port: Id[Port]) -> PhysicalNet | None:
    """The `PhysicalNet` containing `port`, or `None` if `port` is not a port of `model`.

    Args:
        model: The model to read.
        port: The port whose physical net is looked up.

    Returns:
        `port`'s `PhysicalNet`, or `None` when `port` is not a port of `model`.
    """
    return _closure(model).by_port.get(port)


def _adjacency(model: Model) -> dict[Id[Port], set[Id[Port]]]:
    """Each port's neighbours through the rail closure's conductors, mates and links.

    Every group is made a clique, so a blocked port never cuts the rest of its group off as a hub.
    """
    edges: dict[Id[Port], set[Id[Port]]] = {}

    def join_all(members: Sequence[Id[Port]]) -> None:
        for member in members:
            edges.setdefault(member, set()).update(members)

    for conductor in conductors(model).values():
        join_all((conductor.a, conductor.b))
    for group in link_groups(model, _RAIL_LINKS):
        join_all(group.ports)
    _join_mates(model, join_all)
    return edges


def _condition(model: Model, group: LinkGroup) -> Condition:
    """What a rail needs to pass `group`'s link: its item in the link's state, or nothing.

    A `both` link, a conductive link and every link that no contact state governs need nothing.
    """
    state = link_state(model, group.function, group.link.id)
    return _ALWAYS if state == "both" else frozenset({(group.item, state)})


def _conditional_adjacency(model: Model) -> dict[Id[Port], dict[Id[Port], set[Condition]]]:
    """`_adjacency` with each edge labelled by the conditions of the groups that make it.

    A link's clique carries the link's `_condition`, conductors and mates the empty one.
    Two ports tied by two groups have both labels.
    """
    edges: dict[Id[Port], dict[Id[Port], set[Condition]]] = {}

    def join_all(members: Sequence[Id[Port]], condition: Condition = _ALWAYS) -> None:
        for member in members:
            joined = edges.setdefault(member, {})
            for other in members:
                if other != member:
                    joined.setdefault(other, set()).add(condition)

    for conductor in conductors(model).values():
        join_all((conductor.a, conductor.b))
    for group in link_groups(model, _RAIL_LINKS):
        join_all(group.ports, _condition(model, group))
    _join_mates(model, join_all)
    return edges


def _blocks(own: frozenset[Id[Port]], declared: frozenset[Id[Port]], port: Id[Port]) -> bool:
    """Whether a rail whose own ports are `own` may not enter `port`.

    The one place of the rule: only a net that carries another supplied rail blocks.
    `declared` holds its ports; a net with no potential, or one in no supply, is transparent.
    """
    return port in declared and port not in own


def _rail_sources(model: Model) -> dict[str, set[Id[Port]]]:
    """A rail's own ports: the physical nets of the nets that carry it (model-0140)."""
    known = ports(model)
    sources: dict[str, set[Id[Port]]] = {}
    for net in nets(model).values():
        if net.potential is not None and supply_of_potential(model, net.potential) is not None:
            own = sources.setdefault(net.potential, set())
            for port in (p for p in net.ports if p in known):
                physical = net_of(model, port)
                own.update(physical.ports if physical else (port,))
    return sources


@digest_cached(DIGEST_CACHE_SIZE)
def _rails(model: Model) -> frozendict[Id[Port], frozenset[str]]:
    sources = _rail_sources(model)
    declared = frozenset(port for start in sources.values() for port in start)
    adjacent = _adjacency(model)
    carried: dict[Id[Port], set[str]] = {}
    for rail, start in sources.items():
        own = frozenset(start)
        reached = set(own)
        todo = list(own)
        while todo:
            for neighbour in adjacent.get(todo.pop(), ()):
                if neighbour not in reached and not _blocks(own, declared, neighbour):
                    reached.add(neighbour)
                    todo.append(neighbour)
        for port in reached:
            carried.setdefault(port, set()).add(rail)
    return frozendict({port: frozenset(rails) for port, rails in carried.items()})


def port_rails(model: Model, port: Id[Port]) -> frozenset[str]:
    """The rails `port` carries: the empty set for a port that carries none or is not in `model`.

    A rail is a potential some `SupplySystem` declares and a declared `Net` carries. Each spreads
    from its nets' ports through conductors, mates, `conductive` and `switched` links (contacts
    counted closed) but never enters a net carrying another rail. A changeover's common reached
    from two rails carries both. Only structure is read, never a port name. Which rails stand at
    once: `rail_pairs`. Cached on `model.digest`.

    Args:
        model: The model to read.
        port: The port whose rails are looked up.

    Returns:
        The names of the rails `port` carries.
    """
    return _rails(model).get(port, frozenset[str]())


@dataclasses.dataclass(frozen=True, slots=True)
class _RailStates:
    """For one digest, each rail at each port with its minimal conditions, and ports by function.

    `by_function` lists, sorted, only the ports that carry a rail.
    """

    at_port: frozendict[Id[Port], frozendict[str, frozenset[Condition]]]
    by_function: frozendict[Id[Function], tuple[Id[Port], ...]]


def _consistent(condition: Condition) -> bool:
    """Whether `condition` names no item in two states."""
    return len({item for item, _ in condition}) == len(condition)


def _spread(
    own: frozenset[Id[Port]],
    declared: frozenset[Id[Port]],
    edges: dict[Id[Port], dict[Id[Port], set[Condition]]],
) -> dict[Id[Port], list[Condition]]:
    """The minimal conditions under which a rail whose own ports are `own` reaches each port.

    Same reach and blocking as `_rails`; a path naming one item in two states is dropped.
    Per port only the minimal conditions are kept, an antichain under subset.
    """
    held: dict[Id[Port], list[Condition]] = {port: [_ALWAYS] for port in own}
    todo = [(port, _ALWAYS) for port in own]
    while todo:
        port, condition = todo.pop()
        for neighbour, labels in edges.get(port, {}).items():
            if _blocks(own, declared, neighbour):
                continue
            for label in labels:
                grown = condition | label
                kept = held.get(neighbour, [])
                if not _consistent(grown) or any(other <= grown for other in kept):
                    continue
                held[neighbour] = [*(other for other in kept if not grown <= other), grown]
                todo.append((neighbour, grown))
    return held


@digest_cached(DIGEST_CACHE_SIZE)
def _rail_states(model: Model) -> _RailStates:
    sources = _rail_sources(model)
    declared = frozenset(port for start in sources.values() for port in start)
    edges = _conditional_adjacency(model)
    at_port: dict[Id[Port], dict[str, frozenset[Condition]]] = {}
    for rail, start in sources.items():
        for port, conditions in _spread(frozenset(start), declared, edges).items():
            at_port.setdefault(port, {})[rail] = frozenset(conditions)
    known = ports(model)
    by_function: dict[Id[Function], list[Id[Port]]] = {}
    for port in sorted(at_port):
        by_function.setdefault(known[port].function, []).append(port)
    return _RailStates(
        at_port=frozendict({port: frozendict(rails) for port, rails in at_port.items()}),
        by_function=frozendict({function: tuple(found) for function, found in by_function.items()}),
    )


def _agree(first: Iterable[Condition], second: Iterable[Condition]) -> bool:
    """Whether some condition of `first` and some of `second` can hold together."""
    return any(_consistent(a | b) for a in first for b in second)


def rail_pairs(model: Model, function: Id[Function]) -> frozenset[tuple[str, str]]:
    """The pairs `(low, high)` of rail names, `low < high`, that can stand across `function`.

    Two rails at two different ports of the function, whose conditions agree (no item in two
    states). A `rest` link needs its item at rest, an `operated` link operated, `both` nothing; a
    link only adds a condition, never blocks. Two rails at one port are never a pair. Known limit:
    all contacts of one item move together, so a pair may be missed (it errs towards silence).

    Args:
        model: The model to read.
        function: The function whose standing rail pairs are found.

    Returns:
        Every pair `(low, high)` of rail names that can stand across `function`; empty for a
        function with no pair, an unknown function, or no rail.
    """
    states = _rail_states(model)
    found: set[tuple[str, str]] = set()
    at = [states.at_port[port] for port in states.by_function.get(function, ())]
    for index, first in enumerate(at):
        for second in at[index + 1 :]:
            for a, conditions_a in first.items():
                for b, conditions_b in second.items():
                    pair = (a, b) if a < b else (b, a)
                    if a != b and pair not in found and _agree(conditions_a, conditions_b):
                        found.add(pair)
    return frozenset(found)


def port_groups(groups: Iterable[Sequence[Id[Port]]]) -> tuple[PhysicalNet, ...]:
    """Union-find over caller-given `groups`: each group's own ports become one connected set.

    A caller-scoped sibling of `physical_nets`: the caller decides what is connected, no more.
    Sorted like `physical_nets`, by each group's sorted `ports`; not cached.
    """
    fixed = [tuple(group) for group in groups]
    members: set[Id[Port]] = {port for group in fixed for port in group}
    sets = UnionFind(members)
    for group in fixed:
        sets.union_all(group)
    return _nets_from(sets)
