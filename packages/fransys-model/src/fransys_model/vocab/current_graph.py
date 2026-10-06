"""The current graph of one set of closed links: its raw parts, and the law solved on it.

Split from `current_chains` (RATINGS-2 C3). `raw_of` reads a model once: the `Wire`s that join
ports (conductors, and every link or mate that is no position), the `Edge`s that are the
positions, and the open ends. `solve` and `group` take any subset of them, the links closed in one
item state (`current_states`), and build the multigraph on it: a union-find over the wires gives
the nodes, the positions are the edges, and one outside vertex is joined to every open node. Then
`solve` computes the exact law (`current_bounds.block_bounds`) and `group` gives the blocks.
"""

import dataclasses
from typing import TYPE_CHECKING

from fransys_model.kernel import Id, UnionFind
from fransys_model.vocab.core import Port
from fransys_model.vocab.rating_readers import states_current
from fransys_model.vocab.tables import conductors, functions

from .current_blocks import blocks
from .current_bounds import CurrentBound, Tie, block_bounds, tie_of
from .current_ties import Joint, open_ends, pairs, two_ports

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence

    from fransys_model.kernel import Model
    from fransys_model.vocab.contacts import LinkState
    from fransys_model.vocab.core import Function, Item

_OUTSIDE: Id[Port] = Id[Port](kind="outside", value="outside")


@dataclasses.dataclass(frozen=True, slots=True)
class Wire:
    """Two ports joined while the link is closed: a conductor, or a link or mate with no position.

    A conductor, a mate and a conductive link have no `item` and the `state` `both`; a switched
    link has its item and the state `link_state` names.
    """

    first: Id[Port]
    second: Id[Port]
    item: Id[Item] | None = None
    state: LinkState = "both"


@dataclasses.dataclass(frozen=True, slots=True)
class Edge:
    """One position: `at` is its index in `Raw.edges`, which sorts by functions and ports."""

    at: int
    first: Id[Port]
    second: Id[Port]
    tie: Tie
    item: Id[Item] | None = None
    state: LinkState = "both"


@dataclasses.dataclass(frozen=True, slots=True)
class Raw:
    """The wires, the positions and the open ends of a model, before any link is opened."""

    wires: tuple[Wire, ...]
    edges: tuple[Edge, ...]
    opens: frozenset[Id[Port]]


def _joint_wire(joint: Joint) -> Wire:
    return Wire(joint.first, joint.second, joint.item, joint.state)


def raw_of(model: Model) -> Raw:
    """Read `model` into wires, positions and open ends.

    A link or mate is a position when its function states a current and lies inside one function.
    Else it is a wire; a two-port function no link joins that states a current is a position too.
    """
    stated = {function: states_current(model, function) for function in functions(model)}
    links, mated = pairs(model)
    wires = [Wire(conductor.a, conductor.b) for conductor in conductors(model).values()]
    found: list[tuple[tuple[Id[Function], ...], Joint]] = []
    for joint in links:
        if joint.one == joint.other and stated[joint.one]:
            found.append(((joint.one,), joint))
        else:
            wires.append(_joint_wire(joint))
    for joint in mated:
        if stated[joint.one] or stated[joint.other]:
            found.append((tuple(sorted({joint.one, joint.other})), joint))
        else:
            wires.append(_joint_wire(joint))
    found += [
        ((function,), Joint(first, second, function, function))
        for first, second, function in two_ports(model)
        if stated[function]
    ]
    found.sort(key=lambda entry: (entry[0], entry[1].first, entry[1].second))
    edges = tuple(
        Edge(at, joint.first, joint.second, tie_of(model, through), joint.item, joint.state)
        for at, (through, joint) in enumerate(found)
    )
    return Raw(wires=tuple(wires), edges=edges, opens=open_ends(model))


def _build(
    edges: Iterable[Edge],
    wires: Iterable[Wire],
    opens: Iterable[Id[Port]],
    root: Callable[[Id[Port]], Id[Port]],
) -> tuple[list[Edge], list[tuple[Id[Port], Id[Port]]], list[Tie | None]]:
    """The kept positions (no self-loop), the multigraph's ends and its ties, outside last.

    `root` maps a port to its node under the links that are always closed; `wires` are joined on
    top of it. Every open node gets one edge to the outside vertex, which holds a source.
    """
    local: UnionFind[Id[Port]] = UnionFind()
    for wire in wires:
        local.union(root(wire.first), root(wire.second))
    placed = [(local.find(root(e.first)), local.find(root(e.second)), e) for e in edges]
    kept = sorted((p for p in placed if p[0] != p[1]), key=lambda p: (p[0], p[1], p[2].at))
    opened = sorted({local.find(root(port)) for port in opens})
    ends = [(first, second) for first, second, _ in kept] + [(node, _OUTSIDE) for node in opened]
    ties: list[Tie | None] = [edge.tie for _, _, edge in kept] + [None] * len(opened)
    return [edge for _, _, edge in kept], ends, ties


def solve(
    edges: Sequence[Edge],
    wires: Iterable[Wire],
    opens: Iterable[Id[Port]],
    root: Callable[[Id[Port]], Id[Port]],
) -> dict[int, tuple[CurrentBound, ...]]:
    """The bounds of every position (by `Edge.at`) of the graph the closed parts make."""
    kept, ends, ties = _build(edges, wires, opens, root)
    found: dict[int, tuple[CurrentBound, ...]] = {}
    for block in blocks(ends):
        for index, bounds in block_bounds(block, ends, ties).items():
            found[kept[index].at] = bounds
    return found


def group(
    edges: Sequence[Edge],
    wires: Iterable[Wire],
    opens: Iterable[Id[Port]],
    root: Callable[[Id[Port]], Id[Port]],
) -> list[list[int]]:
    """The blocks of the graph the closed parts make, as lists of `Edge.at`; no outside."""
    kept, ends, _ = _build(edges, wires, opens, root)
    grouped = ([kept[index].at for index in block if index < len(kept)] for block in blocks(ends))
    return [block for block in grouped if block]
