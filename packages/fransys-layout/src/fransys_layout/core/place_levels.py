"""Stage 5, y: trunks of one row and side that overlap in x take distinct levels."""

from __future__ import annotations

from collections import defaultdict
from itertools import combinations, permutations
from typing import TYPE_CHECKING, NamedTuple

from .intervals import levels
from .keys import natural_key
from .place_trunk import trunk_node

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from collections.abc import Set as AbstractSet

    from .constraints import Graph
    from .values import Options

EXACT_LIMIT = 7


class Span(NamedTuple):
    """One fan's trunk in one row once x is solved: extent, depth, side and the x of each end."""

    fan: str
    row: int
    x0: int
    x1: int
    lanes: int
    side: str
    drivers: tuple[int, ...] = ()
    legs: tuple[int, ...] = ()


def trunk_levels(g: Graph, spans: Sequence[Span], options: Options) -> frozenset[str]:
    """Overlapping trunks of one row and side take distinct levels, the order that crosses least.

    A trunk the stacks hold above another stays above it; each pair gets a depth edge.
    Returns the trunks at such an edge: their legs hang loose, so a row of terminals can level.
    """
    below, lowered = _below(g), set[str]()
    for group in _groups(spans):
        order = _level_order(g, below, group)
        level = levels([(s.x0, s.x1) for s in order], range(len(order)))
        for i, upper in enumerate(order):
            for j in range(i + 1, len(order)):
                if level[j] > level[i] and _overlap(upper, order[j]):
                    a, b = trunk_node(upper.fan, upper.row), trunk_node(order[j].fan, order[j].row)
                    g.after(a, b, options.wiring_grid * upper.lanes)
                    below[g.uf.find(a)[0]].add(g.uf.find(b)[0])
                    lowered |= {a, b}
    return frozenset(lowered)


def _overlap(a: Span, b: Span) -> bool:
    return a.x0 <= b.x1 and b.x0 <= a.x1


def _groups(spans: Sequence[Span]) -> list[list[Span]]:
    """The trunks of one row and side that overlap in a chain, each group leftmost first."""
    groups: list[list[Span]] = []
    right = 0
    for s in sorted(spans, key=lambda s: (s.row, s.side, s.x0, s.fan)):
        if groups and (groups[-1][0].row, groups[-1][0].side) == (s.row, s.side) and s.x0 <= right:
            groups[-1].append(s)
            right = max(right, s.x1)
        else:
            groups.append([s])
            right = s.x1
    return groups


def _drop_cost(upper: Span, lower: Span) -> int:
    """The crossings with `upper` above `lower`: its legs drop through lower, lower's drivers up."""
    legs = sum(lower.x0 < x < lower.x1 for x in upper.legs)
    return legs + sum(upper.x0 < x < upper.x1 for x in lower.drivers)


def _level_order(
    g: Graph, below: Mapping[str, AbstractSet[str]], group: Sequence[Span]
) -> Sequence[Span]:
    """The group's trunks from the top level down: fewest crossings, ties leftmost highest."""
    n = len(group)
    if n == 1:
        return group
    cost = [[_drop_cost(a, b) for b in group] for a in group]
    classes = [g.uf.find(trunk_node(s.fan, s.row))[0] for s in group]
    reach = [_reachable(below, c) for c in classes]
    held = [
        [classes[i] != classes[j] and classes[j] in reach[i] for j in range(n)] for i in range(n)
    ]
    ranked = _exact_order(cost, held) if n <= EXACT_LIMIT else _greedy_order(cost, held, group)
    return [group[i] for i in ranked]


def _exact_order(cost: Sequence[Sequence[int]], held: Sequence[Sequence[bool]]) -> tuple[int, ...]:
    """The first of the cheapest orders, trunks numbered leftmost first; held[i][j]: i above j."""
    best, best_cost = tuple(range(len(cost))), None
    for perm in permutations(range(len(cost))):
        pairs = list(combinations(perm, 2))
        if any(held[b][a] for a, b in pairs):
            continue
        total = sum(cost[a][b] for a, b in pairs)
        if best_cost is None or total < best_cost:
            best, best_cost = perm, total
    return best


def _greedy_order(
    cost: Sequence[Sequence[int]], held: Sequence[Sequence[bool]], group: Sequence[Span]
) -> list[int]:
    """Insert the trunks in natural fan order, each where it adds the fewest crossings."""
    order: list[int] = []
    for n in sorted(range(len(cost)), key=lambda i: natural_key(group[i].fan)):
        slots: list[int] = [
            p
            for p in range(len(order) + 1)
            if not any(held[n][m] for m in order[:p]) and not any(held[m][n] for m in order[p:])
        ]
        use: list[int] = slots or [len(order)]
        order.insert(min(_insertion(cost, order, n, p) for p in use)[2], n)
    return order


def _insertion(
    cost: Sequence[Sequence[int]], order: Sequence[int], n: int, p: int
) -> tuple[int, int, int]:
    """What trunk n adds at slot p of `order`: crossings, then inversions, then p."""
    above, under = order[:p], order[p:]
    crossings = sum(cost[m][n] for m in above) + sum(cost[n][m] for m in under)
    return crossings, sum(m > n for m in above) + sum(m < n for m in under), p


def _below(g: Graph) -> defaultdict[str, set[str]]:
    """The class each class has an edge to, as Graph.solve sees the edges."""
    out: defaultdict[str, set[str]] = defaultdict(set)
    for a, b, _ in g.edges:
        ra, rb = g.uf.find(a)[0], g.uf.find(b)[0]
        if ra != rb:
            out[ra].add(rb)
    return out


def _reachable(below: Mapping[str, AbstractSet[str]], start: str) -> set[str]:
    """The classes edges lead to from `start`, itself included."""
    seen, todo = {start}, [start]
    while todo:
        for nxt in below[todo.pop()]:
            if nxt not in seen:
                seen.add(nxt)
                todo.append(nxt)
    return seen
