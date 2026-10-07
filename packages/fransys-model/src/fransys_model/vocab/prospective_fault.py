"""The prospective fault current at each protective position (RATINGS-3 R7 to R10, R17).

Per protective position D and current kind it reaches, the fault graph (`fault_graph`) is solved
per consistent item state of D's component (`current_states.assignments`) and per terminal
(`fault_solve`). D's value is its larger terminal's, the highest over the states (Q8).
"""

import dataclasses
from typing import TYPE_CHECKING
lazy from decimal import Decimal

from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, UnionFind, digest_cached
from fransys_model.vocab.closure import port_rails
from fransys_model.vocab.enums import Current, FunctionKind
lazy from fransys_model.vocab.core import Function, Port
lazy from fransys_model.vocab.supply_system import SupplySystem

from .current_chains import CurrentPosition, position_at
from .current_graph import Edge, Wire, raw_of
from .current_states import assignments, evaluate
from .fault_graph import fault_graph, largest_known
from .fault_solve import NOTHING, Fault, closed_state, highest, terminal_share
from .rail_reach import rails_by_potential, reached_kinds, reached_supplies
from .tables import functions

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Mapping, Sequence

    from .fault_graph import FaultGraph
    from .fault_solve import Closed, Share
    from .voltage import RailV

type _Faults = Mapping[int, list[tuple[Current, frozenset[str]]]]


@dataclasses.dataclass(frozen=True, slots=True)
class ProspectiveFault:
    """The prospective fault current of `kind` at one protective position.

    `current_a` is the largest current a bolted fault at either terminal drives through it, over
    the item states: `None` when a source counted states none, `0` when no source is counted.
    Cable resistance is ignored and parallel runs add, so it errs high; an undeclared feed counts
    as no source. `time_constant_ms` is the largest DC time constant of the sources counted, over
    the states: `None` for AC, or when a counted source states none. `functions` and `supplies`
    are the source functions and the declared supplies counted, sorted.
    """

    position: CurrentPosition
    kind: Current
    current_a: Decimal | None
    time_constant_ms: Decimal | None
    functions: tuple[Id[Function], ...]
    supplies: tuple[Id[SupplySystem], ...]


def _rails(
    lookup: Mapping[str, RailV], systems: Iterable[set[str]], kind: Current
) -> frozenset[str]:
    """The rails of `kind` of the supply systems `systems` (one set per function held)."""
    reached = frozenset[str]().union(*systems)
    ac = kind is Current.AC
    return frozenset(
        name for name, rail in lookup.items() if rail.supply in reached and rail.ac is ac
    )


def _faults(model: Model, graph: FaultGraph) -> dict[int, list[tuple[Current, frozenset[str]]]]:
    """Each protective position of `graph`, with each kind it reaches and its rails of that kind."""
    reached = reached_kinds(model)
    supplies = reached_supplies(model)
    lookup = rails_by_potential(model)
    table = functions(model)
    found: dict[int, list[tuple[Current, frozenset[str]]]] = {}
    for at in graph.branch:
        held = graph.edges[at].tie.functions
        if any(table[f].kind is FunctionKind.PROTECTION for f in held):
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


def _state_shares(
    state: Closed, graph: FaultGraph, faults: _Faults, mine: Sequence[int]
) -> Iterator[tuple[tuple[int, Current], Share]]:
    """Each protective position closed in `state`, per kind: the larger of its two terminals."""
    present = {edge.at for edge in state.edges}
    for at in (at for at in mine if at in present):
        first, second = graph.edges[at].first, graph.edges[at].second
        for kind, rails in faults[at]:
            ends = ((first, second), (second, first))
            shares = [
                terminal_share(state, graph.feeds, Fault(at, a, b, kind, rails)) for a, b in ends
            ]
            yield (at, kind), highest(shares)


def _component_shares(
    model: Model, graph: FaultGraph, faults: _Faults, parts: tuple[list[Edge], list[Wire]]
) -> dict[tuple[int, Current], list[Share]]:
    """Each protective position of one component, per kind: its share in each item state."""
    mine = [edge.at for edge in parts[0] if edge.at in faults]
    found: dict[tuple[int, Current], list[Share]] = {}
    if not mine:
        return found
    for _, closed in assignments((*parts[0], *parts[1])):
        edges = [part for part in closed if isinstance(part, Edge)]
        wires = [part for part in closed if isinstance(part, Wire)]
        state = closed_state(edges, wires, lambda port: port_rails(model, port))
        for key, share in _state_shares(state, graph, faults, mine):
            found.setdefault(key, []).append(share)
    return found


def _over_states(shares: Sequence[Share]) -> Share:
    """The highest over the states (Q8); the time constant the largest of every state counting."""
    if not shares:
        return NOTHING
    constants = [share.time_constant_ms for share in shares if share.counts()]
    return dataclasses.replace(highest(shares), time_constant_ms=largest_known(constants))


@digest_cached(DIGEST_CACHE_SIZE)
def prospective_fault(model: Model) -> tuple[ProspectiveFault, ...]:
    """The prospective fault current at each protective position, per current kind.

    One entry per position whose function is a `protection` one and per kind its rails carry.
    A bolted fault at either terminal joins it to every other rail of its supplies; the loads are
    left out, every source and every declared supply that states a fault current counts. A
    position no source reaches reads `0`.
    """
    raw = raw_of(model)
    graph = fault_graph(model, raw)
    faults = _faults(model, graph)
    if not faults:
        return ()
    bounds, _ = evaluate(raw)
    shares: dict[tuple[int, Current], list[Share]] = {}
    for parts in _components(graph):
        shares.update(_component_shares(model, graph, faults, parts))
    found = []
    for at, kinds in faults.items():
        position = position_at(raw, bounds, graph.branch[at])
        for kind, _ in kinds:
            share = _over_states(shares.get((at, kind), []))
            found.append(
                ProspectiveFault(
                    position,
                    kind,
                    share.current_a,
                    share.time_constant_ms,
                    tuple(sorted(share.functions)),
                    tuple(sorted(share.supplies)),
                )
            )
    return tuple(
        sorted(found, key=lambda f: (f.position.functions, f.position.ports, f.kind.value))
    )
