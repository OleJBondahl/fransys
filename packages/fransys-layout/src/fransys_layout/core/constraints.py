"""Difference constraints solved by longest path: x[b] >= x[a] + d, and x[b] = x[a] + d classes."""

from __future__ import annotations

import heapq
from collections import defaultdict
from typing import TYPE_CHECKING

from .keys import natural_key
from .unionfind import UnionFind

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

ORIGIN = "@origin"

Pred = dict[str, list[tuple[str, int]]]


class Graph:
    """Nodes are strings; equal() merges two into one class, after() adds a minimum distance."""

    def __init__(self) -> None:
        self.nodes: set[str] = {ORIGIN}
        self.uf = UnionFind()
        self.edges: list[tuple[str, str, int]] = []

    def add(self, node: str) -> None:
        """Add a node that no edge names."""
        self.nodes.add(node)

    def equal(self, a: str, b: str, distance: int = 0) -> bool:
        """x[b] = x[a] + distance; False when the two already disagree, and nothing changes."""
        self.nodes.update((a, b))
        return self.uf.union(a, b, distance)

    def after(self, a: str, b: str, distance: int) -> None:
        """x[b] >= x[a] + distance."""
        self.nodes.update((a, b))
        self.edges.append((a, b, distance))

    def at_least(self, node: str, value: int) -> None:
        """x[node] >= value, as an edge from the origin."""
        self.after(ORIGIN, node, value)

    def solve(self) -> dict[str, int] | None:
        """Smallest x per node with the origin at 0; None when no x meets every constraint.

        Any cycle is refused, a zero-weight one too: trunk_levels consults reachability first.
        """
        roots = {n: self.uf.find(n) for n in self.nodes}
        members: dict[str, list[str]] = defaultdict(list)
        for n, (r, _) in roots.items():
            members[r].append(n)
        pred: Pred = defaultdict(list)
        for a, b, d in self.edges:
            ra, oa = roots[a]
            rb, ob = roots[b]
            if ra != rb:
                pred[rb].append((ra, oa + d - ob))
            elif ob - oa < d:
                return None
        order = _topological(list(members), pred)
        if order is None:
            return None
        return _longest(order, pred, members, roots)


def _topological(roots: Sequence[str], pred: Pred) -> list[str] | None:
    """Topological order, smallest natural_key ready root first; None on a cycle."""
    indeg = {r: len(pred[r]) for r in roots}
    succ: dict[str, list[str]] = defaultdict(list)
    for r in roots:
        for p, _ in pred[r]:
            succ[p].append(r)
    ready = [(natural_key(r), r) for r in roots if indeg[r] == 0]
    heapq.heapify(ready)
    out: list[str] = []
    while ready:
        _, r = heapq.heappop(ready)
        out.append(r)
        for s in succ[r]:
            indeg[s] -= 1
            if indeg[s] == 0:
                heapq.heappush(ready, (natural_key(s), s))
    return out if len(out) == len(roots) else None


def _longest(
    order: Sequence[str],
    pred: Pred,
    members: Mapping[str, Sequence[str]],
    roots: Mapping[str, tuple[str, int]],
) -> dict[str, int]:
    """Longest path from the origin to each root in topological order, then each member's offset."""
    x: dict[str, int] = {}
    for r in order:
        x[r] = max([0, *(x[p] + w for p, w in pred[r])])
    out: dict[str, int] = {}
    for r, ms in members.items():
        for m in ms:
            out[m] = x[r] + roots[m][1]
    return out
