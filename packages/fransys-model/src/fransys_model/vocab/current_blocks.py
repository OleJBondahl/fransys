"""The biconnected blocks of a multigraph, as sets of edge indices (RATINGS-2 C3).

Pure and iterative (no recursion, so a long string cannot overflow the stack). Edges are the
positions of `current_chains` and the edges to the outside; a parallel pair of edges is a block
and a bridge is a block of one edge.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Hashable, Iterator, Sequence


def blocks[V: Hashable](edges: Sequence[tuple[V, V]]) -> tuple[frozenset[int], ...]:
    """The blocks of the multigraph whose edge `i` joins `edges[i]`, each as its edge indices.

    Every edge is in exactly one block; the blocks come back ordered by their smallest edge.
    Self-loops are not allowed.
    """
    adjacent: dict[V, list[tuple[int, V]]] = {}
    for at, (one, other) in enumerate(edges):
        adjacent.setdefault(one, []).append((at, other))
        adjacent.setdefault(other, []).append((at, one))
    order: dict[V, int] = {}
    low: dict[V, int] = {}
    stack: list[int] = []
    found: list[frozenset[int]] = []
    for root in adjacent:
        if root not in order:
            found.extend(_component(root, adjacent, order, low, stack))
    return tuple(sorted(found, key=min))


def _component[V: Hashable](
    root: V,
    adjacent: dict[V, list[tuple[int, V]]],
    order: dict[V, int],
    low: dict[V, int],
    stack: list[int],
) -> Iterator[frozenset[int]]:
    """The blocks of the component of `root`: an explicit-stack depth-first search."""
    order[root] = low[root] = len(order)
    frames = [(root, -1, iter(adjacent[root]))]
    while frames:
        vertex, via, neighbours = frames[-1]
        for at, other in neighbours:
            if at == via:
                continue
            if other not in order:
                stack.append(at)
                order[other] = low[other] = len(order)
                frames.append((other, at, iter(adjacent[other])))
                break
            if order[other] < order[vertex]:
                stack.append(at)
                low[vertex] = min(low[vertex], order[other])
        else:
            frames.pop()
            if frames:
                parent = frames[-1][0]
                low[parent] = min(low[parent], low[vertex])
                if low[vertex] >= order[parent]:
                    block = [stack.pop()]
                    while block[-1] != via:
                        block.append(stack.pop())
                    yield frozenset(block)
