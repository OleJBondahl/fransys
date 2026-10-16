"""Stage 1, y cycles: which groups of edges to cut so a directed graph has no cycle.

General technique over plain values. An edge is `(a, b, owners)`: `a` must lie above `b`; an
edge with no owner is fixed, an edge with owners is gone once any owner is cut. The caller
passes the cost of cutting an owner and the key that breaks a tie; this module reads no id text.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence
    from collections.abc import Set as AbstractSet

    type Edge = tuple[str, str, frozenset[str]]


def _finish_order(adj: Mapping[str, Sequence[str]], nodes: Sequence[str]) -> list[str]:
    """Nodes by depth-first finishing time, without recursion."""
    seen: set[str] = set()
    order: list[str] = []
    for start in (n for n in nodes if n not in seen):
        seen.add(start)
        stack = [(start, iter(adj.get(start, ())))]
        while stack:
            node, children = stack[-1]
            nxt = next((c for c in children if c not in seen), None)
            if nxt is None:
                order.append(node)
                stack.pop()
            else:
                seen.add(nxt)
                stack.append((nxt, iter(adj.get(nxt, ()))))
    return order


def cyclic_parts(pairs: Sequence[tuple[str, str]]) -> list[frozenset[str]]:
    """The strongly connected parts that hold a cycle (two nodes, or one with a self edge)."""
    fwd: dict[str, list[str]] = defaultdict(list)
    back: dict[str, list[str]] = defaultdict(list)
    for a, b in pairs:
        fwd[a].append(b)
        back[b].append(a)
    nodes = sorted({n for p in pairs for n in p})
    loops = {a for a, b in pairs if a == b}
    done: set[str] = set()
    parts = []
    for root in reversed(_finish_order(fwd, nodes)):
        if root in done:
            continue
        part = set(_finish_order(back, [root])) - done
        done |= part
        if len(part) > 1 or part & loops:
            parts.append(frozenset(part))
    return sorted(parts, key=min)


def _live(edges: Sequence[Edge], cut: AbstractSet[str]) -> list[tuple[str, str]]:
    return [(a, b) for a, b, owners in edges if not owners & cut]


def _pick(
    edges: Sequence[Edge],
    parts: Sequence[frozenset[str]],
    cut: AbstractSet[str],
    rank: Callable[[str], Any],
) -> str:
    """The cheapest owner of an edge inside a cyclic part; the rank breaks a tie."""
    where = {n: i for i, part in enumerate(parts) for n in part}
    owners = {
        o for a, b, os in edges if where.get(a, -1) == where.get(b, -2) and not os & cut for o in os
    }
    if not owners:
        nodes = ", ".join(sorted(n for part in parts for n in part))
        text = f"a cycle through {nodes} has no edge that can be cut"
        raise ValueError(text)
    return min(owners, key=rank)


def y_cycle_cuts(
    edges: Sequence[Edge], cost: Mapping[str, int], key: Callable[[str], Any]
) -> frozenset[str]:
    """Owners to cut so the rest is acyclic: cheapest first, `key` breaks a tie, none redundant."""
    cut: list[str] = []
    while parts := cyclic_parts(_live(edges, frozenset(cut))):
        cut.append(_pick(edges, parts, frozenset(cut), lambda o: (cost[o], key(o))))
    for owner in reversed(list(cut)):
        rest = frozenset(cut) - {owner}
        if not cyclic_parts(_live(edges, rest)):
            cut.remove(owner)
    return frozenset(cut)
