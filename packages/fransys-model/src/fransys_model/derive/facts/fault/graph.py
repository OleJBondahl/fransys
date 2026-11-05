"""The fault graph: the current graph with the loads out and every source in.

Built once per model from `raw_of`: the wires as they are, the positions minus the loads, a
two-port source that is no position yet as an edge of its own. Open ends join nothing.
"""

import dataclasses
from typing import TYPE_CHECKING, Final
lazy from decimal import Decimal

from fransys_model.derive.facts.current.bounds import tie_of
from fransys_model.derive.facts.current.graph import Edge
from fransys_model.derive.facts.energy_flow import gives_energy, takes_energy
from fransys_model.derive.facts.fault.readers import (
    conductive_ports,
    fault_current,
    fault_time_constant,
)
from fransys_model.derive.facts.rail_reach import reached_kinds
from fransys_model.elecdef import Current
from fransys_model.vocab.tables import functions
lazy from fransys_model.kernel import Id

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping, Sequence

    from fransys_model.derive.facts.current.graph import Raw, Wire
    from fransys_model.kernel import Model
    from fransys_model.vocab.core import Function

_EDGE_PORTS: Final = 2  # a source with exactly two conductive ports is one edge


@dataclasses.dataclass(frozen=True, slots=True)
class Feed:
    """What one source edge gives: its source functions.

    `kinds` are the current kinds the edge reaches; `current` holds the fault current per kind it
    may count for, `None` unstated.
    """

    functions: tuple[Id[Function], ...]
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


def _positions(model: Model, raw: Raw) -> list[tuple[Edge, int | None]]:
    """The positions that are no load, each with its index in `raw`."""
    return [(edge, edge.at) for edge in raw.edges if not all(takes_energy(model, function) for function in edge.tie.functions)]


def _sources(model: Model, raw: Raw) -> list[tuple[Edge, int | None]]:
    """A two-port source that is no position yet, as an edge of its own."""
    held = {function for edge in raw.edges for function in edge.tie.functions}
    found: list[tuple[Edge, int | None]] = []
    for function in functions(model):
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
    current = frozendict({kind: largest_known([fault_current(model, f, kind) for f in sources]) for kind in Current})
    return Feed(
        functions=sources,
        kinds=frozenset(kind for f in sources for kind in reached.get(f, ())),
        current=current,
        time_constant_ms=largest_known([fault_time_constant(model, f) for f in sources]),
    )


def fault_graph(model: Model, raw: Raw) -> FaultGraph:
    """The fault graph of `model`, whose current graph `raw` is (`raw_of`)."""
    reached = reached_kinds(model)
    parts = [*_positions(model, raw), *_sources(model, raw)]
    edges = [edge for edge, _ in parts]
    feeds = {at: feed for at, (edge, _) in enumerate(parts) if (feed := _function_feed(model, edge.tie.functions, reached)) is not None}
    return FaultGraph(
        edges=tuple(dataclasses.replace(edge, at=at) for at, edge in enumerate(edges)),
        wires=raw.wires,
        branch=frozendict({at: of for at, (_, of) in enumerate(parts) if of is not None}),
        feeds=frozendict(feeds),
    )
