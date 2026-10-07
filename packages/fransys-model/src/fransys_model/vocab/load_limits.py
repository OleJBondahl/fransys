"""The limit that bounds each load's draw (RATINGS-3 R4, R14, R15, R17).

A load is added to the current graph alone, as one edge (or a star), so no other load makes a
loop that avoids a fuse. The graph `chain_blocks` reads is not changed: load edges live here only.
"""

import dataclasses
from typing import TYPE_CHECKING, Final
lazy from decimal import Decimal

from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, UnionFind, digest_cached
lazy from fransys_model.vocab.core import Function, Port
lazy from fransys_model.vocab.enums import Current

from .current_bounds import CurrentBound, Tie
from .current_graph import Edge, Raw, raw_of
from .current_states import evaluate
from .energy_flow import takes_energy
from .fault_readers import conductive_ports, draw
from .rail_reach import reached_kinds
from .tables import functions

if TYPE_CHECKING:
    from collections.abc import Mapping

type _Bounds = Mapping[int, tuple[CurrentBound, ...]]
_EDGE_PORTS: Final = 2  # a load with two conductive ports is one edge; more make a star


@dataclasses.dataclass(frozen=True, slots=True)
class LoadLimit:
    """One load edge's draw and the limit that bounds it.

    `port` is the star edge's port, `None` for a two-port load or a load that is already a position.
    """

    function: Id[Function]
    port: Id[Port] | None
    kind: Current
    draw_a: Decimal
    bound: CurrentBound | None


def _pick(bounds: _Bounds, at: int, kind: Current) -> CurrentBound | None:
    """The bound of `kind` at position `at`, if it has one."""
    return next((bound for bound in bounds.get(at, ()) if bound.kind is kind), None)


def _new_edges(function: Id[Function], ports: tuple[Id[Port], ...], start: int) -> list[Edge]:
    """The edges that add `function` to the graph: one for two ports, a star for more."""
    tie = Tie((function,), (), source=False)
    if len(ports) == _EDGE_PORTS:
        return [Edge(start, ports[0], ports[1], tie)]
    star = Id[Port](kind="star", value=function.value)
    return [Edge(start + at, port, star, tie) for at, port in enumerate(ports)]


def _alone(raw: Raw, base: UnionFind[Id[Port]], ports: tuple[Id[Port], ...]) -> Raw:
    """The parts of `raw` in the components `ports` lie on, the edges renumbered from 0."""
    homes = {base.find(port) for port in ports}
    edges = [e for e in raw.edges if base.find(e.first) in homes]
    return Raw(
        wires=tuple(w for w in raw.wires if base.find(w.first) in homes),
        edges=tuple(dataclasses.replace(e, at=at) for at, e in enumerate(edges)),
        opens=frozenset(p for p in raw.opens if base.find(p) in homes),
    )


def _added(
    model: Model,
    raw: Raw,
    base: UnionFind[Id[Port]],
    load: tuple[Id[Function], Decimal, list[Current]],
) -> list[LoadLimit]:
    """The limits of the load `(function, draw, kinds)` added to the graph alone."""
    function, drawn, kinds = load
    ports = conductive_ports(model, function)
    if len(ports) < _EDGE_PORTS:
        return []
    alone = _alone(raw, base, ports)
    new = _new_edges(function, ports, len(alone.edges))
    bounds, _ = evaluate(dataclasses.replace(alone, edges=(*alone.edges, *new)))
    star = len(ports) > _EDGE_PORTS
    return [
        LoadLimit(function, port if star else None, kind, drawn, _pick(bounds, edge.at, kind))
        for port, edge in zip(ports, new, strict=False)
        for kind in kinds
    ]


def _positioned(
    raw: Raw, bounds: _Bounds, load: tuple[Id[Function], Decimal, list[Current]]
) -> list[LoadLimit]:
    """The limits of a load that is already a position, one per position and kind."""
    function, drawn, kinds = load
    return [
        LoadLimit(function, None, kind, drawn, _pick(bounds, edge.at, kind))
        for edge in raw.edges
        if function in edge.tie.functions
        for kind in kinds
    ]


@digest_cached(DIGEST_CACHE_SIZE)
def load_limits(model: Model) -> tuple[LoadLimit, ...]:
    """The draw of each load edge and the limit that bounds it, per current kind (RATINGS-3 R4).

    A load with no stated draw, no current kind or fewer than two conductive ports has no entry.
    One load at a time is added to the graph, so the loads never bound each other.
    """
    raw = raw_of(model)
    reached = reached_kinds(model)
    loads = [
        (function, drawn, [kind for kind in Current if kind in reached.get(function, set())])
        for function in functions(model)
        if takes_energy(model, function) and (drawn := draw(model, function)) is not None
    ]
    held = {function for edge in raw.edges for function in edge.tie.functions}
    bounds = evaluate(raw)[0] if any(load[0] in held for load in loads) else {}
    base: UnionFind[Id[Port]] = UnionFind()
    for part in (*raw.wires, *raw.edges):
        base.union(part.first, part.second)
    found: list[LoadLimit] = []
    for load in loads:
        if load[0] in held:
            found += _positioned(raw, bounds, load)
        elif load[2]:
            found += _added(model, raw, base, load)
    return tuple(sorted(found, key=lambda limit: limit.function))
