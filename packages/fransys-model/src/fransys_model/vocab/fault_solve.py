"""The fault at one terminal of a protective position D, in one item state (RATINGS-3 R8, R10).

The fault vertex F joins D's terminal `a` to every node carrying another rail of D's supplies.
With D removed, the blocks every F-b path crosses are in series: the largest counts. In a block
the runs of sources add, each at its largest member; one supply vertex counts once per block.
"""

import collections
import dataclasses
from decimal import Decimal
from typing import TYPE_CHECKING

from fransys_model.kernel import Id, UnionFind
from fransys_model.vocab.core import Port
from fransys_model.vocab.enums import Current

from .current_blocks import blocks
from .fault_graph import largest_known

if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Iterable, Mapping, Sequence

    from fransys_model.vocab.core import Function
    from fransys_model.vocab.supply_system import SupplySystem

    from .current_graph import Edge, Wire
    from .fault_graph import Feed

_FAULT: Id[Port] = Id[Port](kind="fault", value="fault")
_JOINT: int = 2  # a node two edges touch joins two sources into one run


@dataclasses.dataclass(frozen=True, slots=True)
class Share:
    """The fault current the sources counted give, `None` when one lacks it, and those sources."""

    current_a: Decimal | None
    time_constant_ms: Decimal | None
    functions: frozenset[Id[Function]] = frozenset()
    supplies: frozenset[Id[SupplySystem]] = frozenset()

    def counts(self) -> bool:
        """Whether any source is counted."""
        return bool(self.functions or self.supplies)


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
    edges: Sequence[Edge], wires: Iterable[Wire], rails_of: Callable[[Id[Port]], frozenset[str]]
) -> Closed:
    """The `Closed` of the edges and wires one assignment closes (`current_states.assignments`)."""
    nodes: UnionFind[Id[Port]] = UnionFind()
    for wire in wires:
        nodes.union(wire.first, wire.second)
    rails: dict[Id[Port], set[str]] = {}
    ends = {end for edge in edges for end in (edge.first, edge.second)}
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
        frozenset().union(*(share.supplies for share in tied)),
    )


def _rank(share: Share) -> tuple[bool, Decimal]:
    return (share.current_a is None, share.current_a or Decimal(0))


def _summed(shares: Sequence[Share]) -> Share:
    """The runs of one block added (R8): unknown when one is."""
    values = [share.current_a for share in shares]
    known = [value for value in values if value is not None]
    return Share(
        sum(known, Decimal(0)) if len(known) == len(values) else None,
        largest_known([share.time_constant_ms for share in shares]),
        frozenset().union(*(share.functions for share in shares)),
        frozenset().union(*(share.supplies for share in shares)),
    )


def _run_share(feeds: Sequence[Feed], kind: Current) -> Share | None:
    """One run at its largest member, if one reaches `kind`; a supply of another kind is out."""
    counted = [feed for feed in feeds if kind in feed.current]
    if not counted or not any(kind in feed.kinds for feed in feeds):
        return None
    return Share(
        largest_known([feed.current[kind] for feed in counted]),
        largest_known([f.time_constant_ms for f in counted]) if kind is Current.DC else None,
        frozenset(function for feed in counted for function in feed.functions),
        frozenset(supply for feed in counted for supply in feed.supplies),
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
    """Source edges joined end to end at a node no other edge touches, and one supply's edges."""
    runs: UnionFind[int] = UnionFind()
    for node, touching in _adjacent(ends).items():
        if len(touching) == _JOINT and node not in fixed and all(feeds[at] for at, _ in touching):
            runs.union(touching[0][0], touching[1][0])
    by_supply: dict[str, int] = {}
    for at, feed in enumerate(feeds):
        if feed is not None and feed.supply is not None:
            runs.union(by_supply.setdefault(feed.supply, at), at)
    return runs


def _block_share(
    block: frozenset[int], feeds: Sequence[Feed | None], runs: UnionFind[int], kind: Current
) -> Share:
    """A block's runs added (R8); a block with no source of `kind` gives nothing."""
    grouped: dict[int, list[Feed]] = {}
    for at in sorted(block):
        feed = feeds[at]
        if feed is not None:
            grouped.setdefault(runs.find(at), []).append(feed)
    counted = [share for run in grouped.values() if (share := _run_share(run, kind)) is not None]
    return _summed(counted) if counted else NOTHING


def terminal_share(closed: Closed, feeds: Mapping[int, Feed], fault: Fault) -> Share:
    """What the fault at `fault.a` draws through D: the largest block on the F-b path."""
    merged = _fault_nodes(closed, closed.node(fault.a), fault.rails)
    goal = closed.node(fault.b)
    ends: list[tuple[Id[Port], Id[Port]]] = []
    on: list[Feed | None] = []
    for edge in closed.edges:
        one, other = (
            _FAULT if n in merged else n
            for n in (closed.node(edge.first), closed.node(edge.second))
        )
        if edge.at != fault.at and one != other:
            ends.append((one, other))
            on.append(feeds.get(edge.at))
    path = _path(ends, goal) if goal not in merged else frozenset()
    if not path:
        return NOTHING
    runs = _runs(ends, on, {_FAULT, goal})
    return highest(
        [_block_share(block, on, runs, fault.kind) for block in blocks(ends) if block & path]
    )
