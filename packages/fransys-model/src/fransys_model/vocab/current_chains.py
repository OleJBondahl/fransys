"""Current chains: which rated current paths share a loop, and what bounds each (RATINGS-2 C3).

Lives in `vocab` because `validators/ratings_current.py` reads it; `derive.current_chains`
re-exports it (decision model-0088, as `derive.closure` does for the closure).

The graph is a multigraph on the kernel's union-find nodes (`current_graph`): the ports joined
only by conductors and by the links and mates that state no current, and by every link across
two functions (a plain wire for this purpose). Its edges are the positions, the rated links,
mates and two-port functions, and one edge to a single vertex, the outside, from every open node
(`current_ties.open_ends`). The outside holds a source and states no limit. A node with one
position is a dead end, not open: no loop passes it. The exact law of `current_bounds` gives
every position its bound, per consistent item state (`current_states`); each block of the graph
with every switched link closed is one chain, as a grouping only.

Nodes are the ports joined by conductors and by the links and mates that state no current
(an unrated terminal, or an unrated plug and socket, is a plain wire here). Positions are the
rated ones: an internal link (conductive or switched), a mate's pins, and a two-port function
no link joins internally (a source, a load) that states a current rating or a continuous
limit. A two-port function that states neither is dropped, so the poles it spans never
short; a position with both ends on one node is dropped too. A link across two functions of
one part is a wire (its nodes join); it adds no position. The positions are the edges of a
multigraph, and each block of the graph with every switched link closed (a set of positions
any two of which lie on a common loop) is one `CurrentChain`, as a grouping only.

The law: a limit bounds a position when every loop through the position that holds a source
also passes through the limit. The computation is exact, not a heuristic. It is evaluated
per consistent item state (`current_states`): a switched link is closed in the state
`link_state` names, and all contacts of one item move together, so a changeover's two throws
are never closed at once. The position's `bounds` hold, per current kind, the HIGHEST over
the states of the smallest such limit, and the function that set it (a source's
`max_current_*_a`, or the rating current of a full-range `protection` function) and the
states of the items it depends on. A device is below its bound in some state exactly when
it is below that highest bound. Example: a source limited to 186 A, a 100 A full-range fuse
and a contactor in a string open at both ends give the contactor the bound 100 A set by the
fuse; with a load across the string's two poles the load has no bound and the contactor
keeps its 100 A.

The outside: current can leave the model at an open end, a port of an external item or a
boundary port of a standalone unit that is not `PortRole.INTERNAL` (`current_ties.open_ends`).
All of them join ONE extra vertex, the outside, which holds a source and states no limit.
Nothing else opens a node, since an outside edge adds a source-holding loop and can make a
bound larger, which is a false ERROR. So a string open at two ports is a loop through the
outside and its own source bounds its devices, and a load across its two poles,
which the outside can feed as well, gets no bound from the string. The outside is never a
reported position.

Known limits: a position with no loop through it (a string ending at a real dead end, a
bridge) has no bound, so real strings end at external items or at a standalone unit's
boundary; a device with no conductive port on the path has no position; a device whose paths
cross its own functions (a link between ports of two functions) is a wire for chains: the
link adds no position, and the device's own per-path ratings are not checked. An item whose
contacts move independently is read as one actuator (CS1). At most
`current_states.MAX_ENUMERATED_ITEMS` items with links in both states are enumerated in one
component (the smallest item ids first); the rest are held at rest, so a finding may be
missed but none invented.

Ordered by the chains' positions, so the result is the same for any record order (CLAUDE.md
invariant 7). Cached on `model.digest`, the last few results.
"""

import dataclasses

from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, UnionFind, digest_cached
lazy from fransys_model.vocab.core import Function, Port

from .current_graph import raw_of
from .current_states import evaluate
lazy from .current_bounds import CurrentBound


@dataclasses.dataclass(frozen=True, slots=True)
class CurrentPosition:
    """One rated current path: the functions it passes through, sorted, and its bounds.

    `bounds` holds at most one `CurrentBound` per current kind, AC before DC: the highest, over
    the item states in which the position exists and has one, of the smallest limit the law lets
    reach it, with the function that set it and the item states that give it.
    """

    functions: tuple[Id[Function], ...]
    bounds: tuple[CurrentBound, ...]


@dataclasses.dataclass(frozen=True, slots=True)
class CurrentChain:
    """The positions of one block of the current graph, in the order `derive.current_chains` gives.

    The graph has every switched link closed. A position it shorts, but that exists in some
    state, is a chain alone.
    """

    positions: tuple[CurrentPosition, ...]


@dataclasses.dataclass(frozen=True, slots=True)
class PositionEnds:
    """The two ports of a position and the nodes (all-closed union-find roots) they sit on."""

    first: Id[Port]
    second: Id[Port]
    first_node: Id[Port]
    second_node: Id[Port]


@digest_cached(DIGEST_CACHE_SIZE)
def chain_blocks(model: Model) -> tuple[tuple[CurrentChain, tuple[PositionEnds, ...]], ...]:
    """Each chain with the ends of its positions, aligned; `derive.current_chains` orders them."""
    raw = raw_of(model)
    bounds, groups = evaluate(raw)
    nodes: UnionFind[Id[Port]] = UnionFind()
    for wire in raw.wires:
        nodes.union(wire.first, wire.second)
    # A position that exists in some state but is in no block of the all-closed graph (a wire
    # that is closed there shorts it) keeps its bound, in a chain of its own.
    grouped = {at for block in groups for at in block}
    alone = [[at] for at in sorted(bounds) if at not in grouped]
    found: list[tuple[CurrentChain, tuple[PositionEnds, ...]]] = []
    for block in (*groups, *alone):
        entries = sorted(
            (
                (
                    CurrentPosition(raw.edges[at].tie.functions, bounds.get(at, ())),
                    PositionEnds(
                        raw.edges[at].first,
                        raw.edges[at].second,
                        nodes.find(raw.edges[at].first),
                        nodes.find(raw.edges[at].second),
                    ),
                )
                for at in block
            ),
            key=lambda entry: entry[0].functions,
        )
        found.append((CurrentChain(tuple(e[0] for e in entries)), tuple(e[1] for e in entries)))
    found.sort(key=lambda entry: [p.functions for p in entry[0].positions])
    return tuple(found)


def chains_unordered(model: Model) -> tuple[CurrentChain, ...]:
    """The rated current paths grouped by loop (RATINGS-2 C3), positions by function."""
    return tuple(chain for chain, _ in chain_blocks(model))
