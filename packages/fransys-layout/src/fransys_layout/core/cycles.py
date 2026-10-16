"""The cycle split as nontree.md counts it: bundles, ladders and cross-links of the graph."""

from __future__ import annotations

from collections import defaultdict

from .keys import natural_key
from .topology_elements import is_free_sided, is_wiring
from .unionfind import UnionFind
from .values import CycleSplit, PlacementProblem

Edges = list[tuple[str, str]]
TWO_PINS = 2
BIG_NET = 4


def _net_groups(problem: PlacementProblem) -> tuple[dict[str, set[str]], dict[str, int]]:
    """Per merged net (junctions join their nets): its non-junction symbols and pin count."""
    syms = {s.id: s for s in problem.symbols}
    wiring = [n for n in problem.nets if is_wiring(n)]
    uf = UnionFind()
    for net in wiring:
        for ref in net.pins:
            if is_free_sided(syms[ref.sym]):
                uf.union(f"n:{net.id}", f"s:{ref.sym}")
    members: dict[str, set[str]] = defaultdict(set)
    sizes: dict[str, int] = defaultdict(int)
    for net in wiring:
        root = uf.find(f"n:{net.id}")[0]
        plain = [r.sym for r in net.pins if not is_free_sided(syms[r.sym])]
        members[root].update(plain)
        sizes[root] += len(plain)
    return members, sizes


def _edges(problem: PlacementProblem, *, drop_big: bool) -> Edges:
    """Net-symbol edges of merged nets that join two symbols; drop_big also drops 4+ pin nets."""
    members, sizes = _net_groups(problem)
    return [
        (root, s)
        for root, ss in members.items()
        if len(ss) >= TWO_PINS and not (drop_big and sizes[root] >= BIG_NET)
        for s in sorted(ss, key=natural_key)
    ]


def _rank(edges: Edges) -> int:
    uf = UnionFind()
    for a, b in edges:
        uf.union(a, b)
    vertices = {v for e in edges for v in e}
    parts = len({uf.find(v)[0] for v in vertices})
    return len(edges) - len(vertices) + parts


def _bundle_rank(edges: Edges) -> tuple[int, Edges]:
    """Two or more two-pin nets between the same two symbols count once; the rest is bundle rank."""
    by_net: dict[str, list[str]] = defaultdict(list)
    for net, sym in edges:
        by_net[net].append(sym)
    pairs: dict[tuple[str, str], int] = defaultdict(int)
    kept: Edges = []
    for net in sorted(by_net, key=natural_key):
        ss = by_net[net]
        if len(ss) == TWO_PINS:
            pairs[ss[0], ss[1]] += 1
            if pairs[ss[0], ss[1]] > 1:
                continue
        kept.extend((net, s) for s in ss)
    return sum(n - 1 for n in pairs.values()), kept


def cycle_split(problem: PlacementProblem) -> CycleSplit:
    """Bundles, ladders (cycles closing only through a 4+ pin net) and cross-links (the rest)."""
    bundles, kept = _bundle_rank(_edges(problem, drop_big=False))
    _, small_kept = _bundle_rank(_edges(problem, drop_big=True))
    full, cross = _rank(kept), _rank(small_kept)
    return CycleSplit(bundles, max(full - cross, 0), cross)
