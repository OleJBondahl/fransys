"""The fault at one terminal of a protective position D, in one item state.

The fault vertex F joins D's terminal `a` to every node carrying another rail of D's supplies.
With D removed, the blocks every F-b path crosses are in series: the largest counts. In a block
the runs of sources add, each at its largest member.
"""

import collections
import dataclasses
from decimal import Decimal
from typing import TYPE_CHECKING

from fransys_model.derive.facts.current.blocks import blocks
from fransys_model.derive.facts.current.graph import Edge, Wire
from fransys_model.derive.facts.fault.graph import largest_known
from fransys_model.elecdef import Current
from fransys_model.kernel import Id, UnionFind
from fransys_model.vocab.core import Port

if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Iterable, Mapping, Sequence

    from fransys_model.derive.facts.fault.graph import Feed
    from fransys_model.vocab.core import Function

_FAULT: Id[Port] = Id[Port](kind="fault", value="fault")
_JOINT: int = 2  # a node two edges touch joins two sources into one run


@dataclasses.dataclass(frozen=True, slots=True)
class Share:
    """The fault current the sources counted give, `None` when one lacks it, and those sources."""

    current_a: Decimal | None
    time_constant_ms: Decimal | None
    functions: frozenset[Id[Function]] = frozenset()

    def counts(self) -> bool:
        """Whether any source is counted."""
        return bool(self.functions)


NOTHING = Share(Decimal(0), None)


@dataclasses.dataclass(frozen=True, slots=True)
class Closed:
    """One item state of one component: its closed edges, each port's node, each node's rails."""

    edges: tuple[Edge, ...]
    node: Callable[[Id[Port]], Id[Port]]
    rails: Mapping[Id[Port], frozenset[str]]


@dataclasses.dataclass(frozen=True, slots=True)
class Fault:
    """A fault of `kind` at terminal `a` of edge `at`, `b` the other; `rails` are D's of `kind`."""

    at: int
    a: Id[Port]
    b: Id[Port]
    kind: Current
    rails: frozenset[str]


def closed_state(
    edges: Sequence[Edge], wires: Iterable[Wire], rails_of: Callable[[Id[Port]], frozenset[str]], loose: Iterable[Id[Port]] = ()
) -> Closed:
    """The `Closed` of the edges and wires one assignment closes; `loose` ports carry their rails too."""
    nodes: UnionFind[Id[Port]] = UnionFind()
    for wire in wires:
        nodes.union(wire.first, wire.second)
    rails: dict[Id[Port], set[str]] = {}
    ends = {end for edge in edges for end in (edge.first, edge.second)} | set(loose)
    for port in ends.union(*nodes.groups().values()):
        rails.setdefault(nodes.find(port), set()).update(rails_of(port))
    named = {node: frozenset(names) for node, names in rails.items()}
    return Closed(tuple(edges), nodes.find, named)


def highest(shares: Sequence[Share]) -> Share:
    """The largest share, an unknown above every value; tied shares join their sources."""
    top = max(shares, key=_rank)
    tied = [share for share in shares if _rank(share) == _rank(top)]
    return Share(
        top.current_a,
        largest_known([share.time_constant_ms for share in tied if share.counts()]),
        frozenset().union(*(share.functions for share in tied)),
    )


def _rank(share: Share) -> tuple[bool, Decimal]:
    return (share.current_a is None, share.current_a or Decimal(0))


def _summed(shares: Sequence[Share]) -> Share:
    """The runs of one block added: unknown when one is."""
    values = [share.current_a for share in shares]
    known = [value for value in values if value is not None]
    return Share(
        sum(known, Decimal(0)) if len(known) == len(values) else None,
        largest_known([share.time_constant_ms for share in shares]),
        frozenset().union(*(share.functions for share in shares)),
    )


def _run_share(feeds: Sequence[Feed], kind: Current) -> Share | None:
    """One run at its largest member, if one reaches `kind`."""
    counted = [feed for feed in feeds if kind in feed.current]
    if not counted or not any(kind in feed.kinds for feed in feeds):
        return None
    return Share(
        largest_known([feed.current[kind] for feed in counted]),
        largest_known([f.time_constant_ms for f in counted]) if kind is Current.DC else None,
        frozenset(function for feed in counted for function in feed.functions),
    )


def _fault_nodes(closed: Closed, at_a: Id[Port], rails: frozenset[str]) -> frozenset[Id[Port]]:
    """`a`'s node and every node carrying another rail of `rails`; all of them when `a` has none."""
    own = closed.rails.get(at_a, frozenset()) & rails
    other = rails - own if own else rails
    return frozenset({at_a, *(node for node, names in closed.rails.items() if names & other)})


def _adjacent(
    ends: Sequence[tuple[Id[Port], Id[Port]]],
) -> dict[Id[Port], list[tuple[int, Id[Port]]]]:
    adjacent: dict[Id[Port], list[tuple[int, Id[Port]]]] = {}
    for at, (one, other) in enumerate(ends):
        adjacent.setdefault(one, []).append((at, other))
        adjacent.setdefault(other, []).append((at, one))
    return adjacent


def _path(ends: Sequence[tuple[Id[Port], Id[Port]]], goal: Id[Port]) -> frozenset[int]:
    """The edges of one shortest path from F to `goal`; empty when `goal` is unreachable."""
    adjacent = _adjacent(ends)
    via: dict[Id[Port], tuple[int, Id[Port]] | None] = {_FAULT: None}
    todo = collections.deque([_FAULT])
    while todo:
        here = todo.popleft()
        for at, there in adjacent.get(here, ()):
            if there not in via:
                via[there] = (at, here)
                todo.append(there)
    found: set[int] = set()
    step = via.get(goal)
    while step is not None:
        found.add(step[0])
        step = via[step[1]]
    return frozenset(found)


def _runs(
    ends: Sequence[tuple[Id[Port], Id[Port]]],
    feeds: Sequence[Feed | None],
    fixed: Collection[Id[Port]],
) -> UnionFind[int]:
    """Source edges joined end to end at a node no other edge touches."""
    runs: UnionFind[int] = UnionFind()
    for node, touching in _adjacent(ends).items():
        if len(touching) == _JOINT and node not in fixed and all(feeds[at] for at, _ in touching):
            runs.union(touching[0][0], touching[1][0])
    return runs


def _block_share(block: frozenset[int], feeds: Sequence[Feed | None], runs: UnionFind[int], kind: Current) -> Share:
    """A block's runs added; a block with no source of `kind` gives nothing."""
    grouped: dict[int, list[Feed]] = {}
    for at in sorted(block):
        feed = feeds[at]
        if feed is not None:
            grouped.setdefault(runs.find(at), []).append(feed)
    counted = [share for run in grouped.values() if (share := _run_share(run, kind)) is not None]
    return _summed(counted) if counted else NOTHING


def _fault_ends(closed: Closed, merged: frozenset[Id[Port]], parts: Iterable[Edge | Wire]) -> list[tuple[Id[Port], Id[Port], Edge | Wire]]:
    """Each of `parts` with its end nodes, the merged ones as F; a part with both ends at one node is left out."""
    found = []
    for part in parts:
        one, other = (_FAULT if n in merged else n for n in (closed.node(part.first), closed.node(part.second)))
        if one != other:
            found.append((one, other, part))
    return found


def terminal_share(closed: Closed, feeds: Mapping[int, Feed], fault: Fault) -> Share:
    """What the fault at `fault.a` draws through D: the largest block on the F-b path."""
    merged = _fault_nodes(closed, closed.node(fault.a), fault.rails)
    goal = closed.node(fault.b)
    found = _fault_ends(closed, merged, (edge for edge in closed.edges if edge.at != fault.at))
    ends = [(one, other) for one, other, _ in found]
    on = [feeds.get(part.at) if isinstance(part, Edge) else None for _, _, part in found]
    path = _path(ends, goal) if goal not in merged else frozenset()
    if not path:
        return NOTHING
    runs = _runs(ends, on, {_FAULT, goal})
    return highest([_block_share(block, on, runs, fault.kind) for block in blocks(ends) if block & path])


def _own_varies(base: Closed, switched: Sequence[Wire], at_a: Id[Port], rails: frozenset[str]) -> bool:
    """Whether a switched wire can give `a`'s node a rail of `rails` that its own node lacks."""
    adjacent: dict[Id[Port], list[Id[Port]]] = {}
    for wire in switched:
        one, other = base.node(wire.first), base.node(wire.second)
        adjacent.setdefault(one, []).append(other)
        adjacent.setdefault(other, []).append(one)
    seen, todo = {at_a}, [at_a]
    while todo:
        for there in adjacent.get(todo.pop(), ()):
            if there not in seen:
                seen.add(there)
                todo.append(there)
    own = base.rails.get(at_a, frozenset()) & rails
    return any((base.rails.get(node, frozenset()) & rails) - own for node in seen)


def _joints(found: Sequence[tuple[Id[Port], Id[Port], Edge | Wire]], on_chain: Collection[int], feeds: Mapping[int, Feed]) -> frozenset[Id[Port]]:
    """The nodes of each cluster, joined by switched wires apart from F, that two or more source ends of the chain touch.

    A part dangling at such a joint changes the joint's degree, so it changes which sources run on in series (`_runs`).
    """
    cluster: UnionFind[Id[Port]] = UnionFind()
    for one, other, part in found:
        if isinstance(part, Wire) and _FAULT not in (one, other):
            cluster.union(one, other)
    touching = collections.Counter(
        cluster.find(node)
        for one, other, part in (found[at] for at in on_chain)
        if isinstance(part, Edge) and part.at in feeds
        for node in (one, other)
        if node != _FAULT
    )
    return frozenset(node for ends in found for node in ends[:2] if node != _FAULT and touching[cluster.find(node)] >= _JOINT)


def chain(base: Closed, switched: Sequence[Wire], feeds: Mapping[int, Feed], fault: Fault) -> list[Edge | Wire] | None:
    """The parts the value `terminal_share` gives for `fault` can depend on in any item state; `None` when it is nothing in all.

    The blocks an F-b path crosses stand in series, so an item in one can open another; add the parts at a joint of
    their sources, and everything when a switched wire can give `a`'s node a rail of its own.
    """
    live = [*(edge for edge in base.edges if edge.at != fault.at), *switched]
    at_a = base.node(fault.a)
    if _own_varies(base, switched, at_a, fault.rails):
        return live
    merged = _fault_nodes(base, at_a, fault.rails)
    found = _fault_ends(base, merged, live)
    ends = [(one, other) for one, other, _ in found]
    path = _path(ends, base.node(fault.b)) if base.node(fault.b) not in merged else frozenset()
    if not path:
        return None
    on_chain = {at for block in blocks(ends) if block & path for at in block}
    joints = _joints(found, on_chain, feeds)
    return [part for at, (one, other, part) in enumerate(found) if at in on_chain or joints & {one, other}]
