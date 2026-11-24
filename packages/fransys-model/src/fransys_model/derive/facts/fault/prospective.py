"""The prospective fault current at each protective position.

Per protective position D and current kind it reaches, the fault graph (`fault_graph`) is solved per
terminal (`terminal_share`) in each item state of D's chain (`chain`, `states.assignments`). D's value is
its larger terminal's, the highest over the states. A chain of more items than `[ratings] max_solves`
allows is named (`oversized_chains`), never held.
"""

import dataclasses
import functools
from typing import TYPE_CHECKING
lazy from decimal import Decimal

from fransys_model.derive.facts.closure import port_rails
from fransys_model.derive.facts.current.chains import CurrentPosition, evaluated, position_at
from fransys_model.derive.facts.current.graph import Edge, Wire, raw_of
from fransys_model.derive.facts.current.states import assignments, closed, stateful_items, switched
from fransys_model.derive.facts.fault.graph import fault_graph, largest_known
from fransys_model.derive.facts.fault.solve import (
    NOTHING,
    Fault,
    chain,
    closed_state,
    highest,
    terminal_share,
)
from fransys_model.derive.facts.house_settings import ratings_form_of
from fransys_model.derive.facts.rail_reach import (
    rails_by_potential,
    reached_kinds,
    reached_supplies,
)
from fransys_model.derive.facts.roles import function_role
from fransys_model.elecdef import Current
from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, UnionFind, digest_cached
lazy from fransys_model.vocab.core import Function, Port

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence

    from fransys_model.derive.facts.contacts import LinkState
    from fransys_model.derive.facts.fault.graph import FaultGraph
    from fransys_model.derive.facts.fault.solve import Closed, Share
    from fransys_model.vocab.core import Item
    from fransys_model.vocab.voltage import RailV

type _Faults = Mapping[int, list[tuple[Current, frozenset[str]]]]


@dataclasses.dataclass(frozen=True, slots=True)
class ProspectiveFault:
    """The prospective fault current of `kind` at one protective position.

    `current_a` is the largest current a bolted fault at either terminal drives through it, over
    the item states: `None` when a source counted states none, `0` when no source is counted.
    Cable resistance is ignored and parallel runs add, so it errs high; an undeclared feed counts
    as no source. `time_constant_ms` is the largest DC time constant of the sources counted, over
    the states: `None` for AC, or when a counted source states none. `functions` are the
    source functions counted, sorted.
    """

    position: CurrentPosition
    kind: Current
    current_a: Decimal | None
    time_constant_ms: Decimal | None
    functions: tuple[Id[Function], ...]


def _rails(lookup: Mapping[str, RailV], systems: Iterable[set[str]], kind: Current) -> frozenset[str]:
    """The rails of `kind` of the supply systems `systems` (one set per function held)."""
    reached = frozenset[str]().union(*systems)
    ac = kind is Current.AC
    return frozenset(name for name, rail in lookup.items() if rail.supply in reached and rail.ac is ac)


def _faults(model: Model, graph: FaultGraph) -> dict[int, list[tuple[Current, frozenset[str]]]]:
    """Each protective position of `graph`, with each kind it reaches and its rails of that kind."""
    reached = reached_kinds(model)
    supplies = reached_supplies(model)
    lookup = rails_by_potential(model)
    found: dict[int, list[tuple[Current, frozenset[str]]]] = {}
    for at in graph.branch:
        held = graph.edges[at].tie.functions
        if any(function_role(model, f).protects for f in held):
            kinds = [k for k in Current if any(k in reached.get(f, ()) for f in held)]
            systems = [supplies.get(f, set()) for f in held]
            found[at] = [(kind, _rails(lookup, systems, kind)) for kind in kinds]
    return found


def _components(graph: FaultGraph) -> list[tuple[list[Edge], list[Wire]]]:
    """The edges and wires of each connected part of the graph with every link closed."""
    every: UnionFind[Id[Port]] = UnionFind()
    for part in (*graph.wires, *graph.edges):
        every.union(part.first, part.second)
    edges: dict[Id[Port], list[Edge]] = {}
    for edge in graph.edges:
        edges.setdefault(every.find(edge.first), []).append(edge)
    wires: dict[Id[Port], list[Wire]] = {}
    for wire in graph.wires:
        wires.setdefault(every.find(wire.first), []).append(wire)
    return [(members, wires.get(key, [])) for key, members in edges.items()]


@dataclasses.dataclass(frozen=True, slots=True)
class _Position:
    """A protective position D of one component, its own item pinned to the state that closes it.

    `base` holds the edges and `fixed` wires closed in that state; `switched` are the other wires closed in it.
    """

    edge: Edge
    pin: Mapping[Id[Item], LinkState]
    base: Closed
    switched: Sequence[Wire]
    fixed: Sequence[Wire]
    rails_of: Callable[[Id[Port]], frozenset[str]]


def _position(rails_of: Callable[[Id[Port]], frozenset[str]], parts: tuple[list[Edge], list[Wire]], edge: Edge) -> _Position:
    """Position `edge` of one component, its item at the state that closes it."""
    edges, wires = parts
    pin = {edge.item: edge.state} if edge.item is not None and switched(edge) else {}
    fixed = [wire for wire in wires if not switched(wire)]
    live = [wire for wire in wires if switched(wire) and closed(wire, pin)]
    base = closed_state([e for e in edges if closed(e, pin)], fixed, rails_of, (port for wire in live for port in (wire.first, wire.second)))
    return _Position(edge, pin, base, live, fixed, rails_of)


def _states(pos: _Position, parts: Sequence[Edge | Wire], items: Sequence[Id[Item]]) -> Iterator[Closed]:
    """D with the fixed wires and `parts` closed, in each assignment of `items`."""
    for _, kept in assignments(parts, items):
        edges = [pos.edge, *(part for part in kept if isinstance(part, Edge))]
        yield closed_state(edges, [*pos.fixed, *(part for part in kept if isinstance(part, Wire))], pos.rails_of)


def _kind_share(graph: FaultGraph, pos: _Position, kind: Current, rails: frozenset[str], budget: int) -> tuple[Share, tuple[Id[Item], ...]]:
    """D's value of `kind` over the item states of its chain, and the chain's items when too many to walk.

    Both terminals' chains are walked together (the share of a state is the larger terminal's). Over the budget
    (2^n states for n items) no item is walked, all are closed, and the items are named.
    """
    ends = ((pos.edge.first, pos.edge.second), (pos.edge.second, pos.edge.first))
    faults = [Fault(pos.edge.at, a, b, kind, rails) for a, b in ends]
    plans = [chain(pos.base, pos.switched, graph.feeds, fault) for fault in faults]
    live = [fault for fault, plan in zip(faults, plans, strict=True) if plan is not None]
    if not live:
        return NOTHING, ()
    joined = list({id(part): part for plan in plans if plan is not None for part in plan}.values())
    items = [item for item in stateful_items(joined)[0] if item not in pos.pin]
    over = 2 ** len(items) > budget
    shares = [highest([terminal_share(state, graph.feeds, fault) for fault in live]) for state in _states(pos, joined, [] if over else items)]
    return _over_states(shares), tuple(items) if over else ()


def _component_shares(
    model: Model, graph: FaultGraph, faults: _Faults, parts: tuple[list[Edge], list[Wire]], budget: int
) -> tuple[dict[tuple[int, Current], Share], list[tuple[Id[Item], ...]]]:
    """Each protective position of one component, per kind: its share, and the chains too large to walk."""
    rails_of = functools.partial(port_rails, model)
    found: dict[tuple[int, Current], Share] = {}
    over: list[tuple[Id[Item], ...]] = []
    for edge in (edge for edge in parts[0] if edge.at in faults):
        pos = _position(rails_of, parts, edge)
        for kind, rails in faults[edge.at]:
            found[edge.at, kind], named = _kind_share(graph, pos, kind, rails, budget)
            over += [named] if named else []
    return found, over


def _over_states(shares: Sequence[Share]) -> Share:
    """The highest over the states; the time constant the largest of every state counting."""
    if not shares:
        return NOTHING
    constants = [share.time_constant_ms for share in shares if share.counts()]
    return dataclasses.replace(highest(shares), time_constant_ms=largest_known(constants))


@digest_cached(DIGEST_CACHE_SIZE)
def _readings(model: Model) -> tuple[tuple[ProspectiveFault, ...], tuple[tuple[Id[Item], ...], ...]]:
    """The prospective faults and the chains too large to walk: the one walk `prospective_fault` and `oversized_chains` share."""
    raw = raw_of(model)
    graph = fault_graph(model, raw)
    faults = _faults(model, graph)
    if not faults:
        return (), ()
    bounds = evaluated(model)[0]
    budget = ratings_form_of(model).max_solves
    shares: dict[tuple[int, Current], Share] = {}
    over: dict[tuple[Id[Item], ...], None] = {}
    for parts in _components(graph):
        found, named = _component_shares(model, graph, faults, parts, budget)
        shares.update(found)
        over.update(dict.fromkeys(named))
    found_faults = [
        ProspectiveFault(position_at(raw, bounds, graph.branch[at]), kind, share.current_a, share.time_constant_ms, tuple(sorted(share.functions)))
        for at, kinds in faults.items()
        for kind, _ in kinds
        for share in (shares.get((at, kind), NOTHING),)
    ]
    ordered = sorted(found_faults, key=lambda f: (f.position.functions, f.position.ports, f.kind.value))
    return tuple(ordered), tuple(over)


def prospective_fault(model: Model) -> tuple[ProspectiveFault, ...]:
    """The prospective fault current at each protective position, per current kind.

    One entry per position whose function is a `protection` one and per kind its rails carry.
    A bolted fault at either terminal joins it to every other rail of its supplies; the loads are
    left out, every source counts. A position no source reaches reads `0`. Each position is walked
    over every item state of its chain (`chain`).
    """
    return _readings(model)[0]


def oversized_chains(model: Model) -> tuple[tuple[Id[Item], ...], ...]:
    """The items of each chain whose state walk is over the `[ratings] max_solves` budget; `RATING_STATES_OVER_BUDGET` names them."""
    return _readings(model)[1]
