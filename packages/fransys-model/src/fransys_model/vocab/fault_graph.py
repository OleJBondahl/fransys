"""The fault graph (RATINGS-3 R7, Q4): the current graph with the loads out and every source in.

Built once per model from `raw_of`: the wires as they are, the positions minus the loads, a
two-port source that is no position yet as an edge of its own, and one vertex per supply name
whose source declarations state a fault current, joined to each of its pins. Open ends join
nothing: a feed from outside counts only through a declared supply.
"""

import dataclasses
from typing import TYPE_CHECKING, Final
lazy from decimal import Decimal

from fransys_model.kernel import Id
from fransys_model.vocab.core import Port
from fransys_model.vocab.enums import Current

from .current_bounds import Tie, tie_of
from .current_graph import Edge
from .energy_flow import gives_energy, takes_energy
from .fault_readers import conductive_ports, fault_current, fault_time_constant
from .rail_reach import reached_kinds
from .supply_sources import source_declarations, supply_pins
from .tables import functions

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping, Sequence

    from fransys_model.kernel import Model
    from fransys_model.vocab.core import Function
    from fransys_model.vocab.supply_system import SupplySystem

    from .current_graph import Raw, Wire

_EDGE_PORTS: Final = 2  # a source with exactly two conductive ports is one edge (R13, Q11)


@dataclasses.dataclass(frozen=True, slots=True)
class Feed:
    """What one source edge gives: its source functions, or the supply vertex it joins.

    `supply` names that vertex, whose edges count once per block; `kinds` are the current kinds
    the edge reaches; `current` holds the fault current per kind it may count for, `None` unstated.
    """

    functions: tuple[Id[Function], ...]
    supplies: tuple[Id[SupplySystem], ...]
    supply: str | None
    kinds: frozenset[Current]
    current: frozendict[Current, Decimal | None]
    time_constant_ms: Decimal | None


@dataclasses.dataclass(frozen=True, slots=True)
class FaultGraph:
    """The edges (`Edge.at` is the index here) and wires of the fault graph.

    `branch` maps a position's index here to its index in `raw_of`; `feeds` holds the source edges.
    """

    edges: tuple[Edge, ...]
    wires: tuple[Wire, ...]
    branch: frozendict[int, int]
    feeds: frozendict[int, Feed]


def largest_known(values: Sequence[Decimal | None]) -> Decimal | None:
    """The largest of `values`; `None` when any is `None` (an unknown makes it unknown) or none."""
    known = [value for value in values if value is not None]
    return max(known) if known and len(known) == len(values) else None


def supply_vertex(name: str) -> Id[Port]:
    """The vertex of the supply `name`, joined to each of its pins."""
    return Id[Port](kind="supply", value=name)


def _positions(model: Model, raw: Raw) -> list[tuple[Edge, int | None]]:
    """The positions that are no load (Q5), each with its index in `raw`."""
    return [
        (edge, edge.at)
        for edge in raw.edges
        if not all(takes_energy(model, function) for function in edge.tie.functions)
    ]


def _sources(model: Model, raw: Raw) -> list[tuple[Edge, int | None]]:
    """A two-port source that is no position yet, as an edge of its own (Q4)."""
    held = {function for edge in raw.edges for function in edge.tie.functions}
    found: list[tuple[Edge, int | None]] = []
    for function in sorted(functions(model)):
        if function in held or not gives_energy(model, function):
            continue
        ports = conductive_ports(model, function)
        if len(ports) == _EDGE_PORTS:
            found.append((Edge(0, ports[0], ports[1], tie_of(model, (function,), ports)), None))
    return found


def _function_feed(
    model: Model,
    on_edge: Sequence[Id[Function]],
    reached: Mapping[Id[Function], Collection[Current]],
) -> Feed | None:
    """The feed of a position or source edge that holds a source function, else `None`."""
    sources = tuple(function for function in on_edge if gives_energy(model, function))
    if not sources:
        return None
    current = frozendict(
        {kind: largest_known([fault_current(model, f, kind) for f in sources]) for kind in Current}
    )
    return Feed(
        functions=sources,
        supplies=(),
        supply=None,
        kinds=frozenset(kind for f in sources for kind in reached.get(f, ())),
        current=current,
        time_constant_ms=largest_known([fault_time_constant(model, f) for f in sources]),
    )


def _supply_feed(name: str, declared: Sequence[SupplySystem]) -> Feed | None:
    """The feed of the supply `name`, if a source declaration of it states a fault current."""
    stating = [supply for supply in declared if supply.fault_current_a is not None]
    if not stating:
        return None
    # Declarations that differ are SUPPLY_DIFFERS's ERROR; the largest errs high.
    largest = max(s.fault_current_a for s in stating if s.fault_current_a is not None)
    kind = stating[0].current
    constants = [s.fault_time_constant_ms for s in stating if s.fault_time_constant_ms is not None]
    return Feed(
        functions=(),
        supplies=tuple(supply.id for supply in stating),
        supply=name,
        kinds=frozenset({kind}),
        current=frozendict({kind: largest}),
        time_constant_ms=max(constants, default=None),
    )


def _supplies(model: Model) -> list[tuple[Edge, Feed]]:
    """One source edge from each supply vertex to each of its pins (R7)."""
    declared = source_declarations(model)
    tie = Tie((), (), source=True)
    found: list[tuple[Edge, Feed]] = []
    for name, pins in sorted(supply_pins(model).items()):
        feed = _supply_feed(name, declared[name])
        if feed is not None:
            found += [(Edge(0, supply_vertex(name), pin, tie), feed) for pin in sorted(pins)]
    return found


def fault_graph(model: Model, raw: Raw) -> FaultGraph:
    """The fault graph of `model`, whose current graph `raw` is (`raw_of`)."""
    reached = reached_kinds(model)
    parts = [*_positions(model, raw), *_sources(model, raw)]
    supplied = _supplies(model)
    edges = [edge for edge, _ in parts] + [edge for edge, _ in supplied]
    feeds = {
        at: feed
        for at, (edge, _) in enumerate(parts)
        if (feed := _function_feed(model, edge.tie.functions, reached)) is not None
    }
    feeds.update({len(parts) + at: feed for at, (_, feed) in enumerate(supplied)})
    return FaultGraph(
        edges=tuple(dataclasses.replace(edge, at=at) for at, edge in enumerate(edges)),
        wires=raw.wires,
        branch=frozendict({at: of for at, (_, of) in enumerate(parts) if of is not None}),
        feeds=frozendict(feeds),
    )
