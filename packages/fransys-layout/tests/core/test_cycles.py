"""Tests for core/cycles.py: bundles, ladders and cross-links add up to the graph's cycle rank."""

from __future__ import annotations

from fransys_layout.core.cycles import cycle_split
from fransys_layout.core.values import CycleSplit, PlacementProblem, Rail

from .flow_builders import elem, free, net, problem


def independent_rank(prob: PlacementProblem) -> int:
    """Cycle rank of nontree.md's graph: symbols and nets, junctions merge nets, rails go."""
    junction = {s.id for s in prob.symbols if len(s.nodes) == 1 and len(s.pins) > 1}
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    wires = [
        n for n in prob.nets if n.rail is None or n.rail.power not in {"SUPPLY", "GROUND", "PE"}
    ]
    for n in wires:
        for ref in n.pins:
            if ref.sym in junction:
                parent[find(n.id)] = find("J" + ref.sym)
    groups: dict[str, set[str]] = {}
    for n in wires:
        groups.setdefault(find(n.id), set()).update(r.sym for r in n.pins if r.sym not in junction)
    edges = [(g, s) for g, ss in groups.items() if len(ss) >= 2 for s in ss]
    verts = {v for e in edges for v in e}
    comp = {v: v for v in verts}

    def root(v: str) -> str:
        while comp[v] != v:
            v = comp[v]
        return v

    for a, b in edges:
        comp[root(a)] = root(b)
    return len(edges) - len(verts) + len({root(v) for v in verts})


def _split_and_rank(prob: PlacementProblem) -> tuple[CycleSplit, int]:
    split = cycle_split(prob)
    assert split.bundles + split.ladders + split.cross_links == independent_rank(prob)
    return split, independent_rank(prob)


def test_a_tree_has_no_cycles() -> None:
    prob = problem(
        [elem("a"), elem("b"), elem("c")], [net("w1", "a.s", "b.n"), net("w2", "b.s", "c.n")]
    )
    assert _split_and_rank(prob)[0] == CycleSplit(0, 0, 0)


def test_parallel_two_pin_nets_between_two_symbols_are_one_bundle() -> None:
    prob = problem([elem("a"), elem("b")], [net("w1", "a.n", "b.n"), net("w2", "a.s", "b.s")])
    assert _split_and_rank(prob)[0] == CycleSplit(1, 0, 0)


def test_parts_in_parallel_between_two_buses_are_a_ladder() -> None:
    syms = [elem(s) for s in ("a", "b", "x", "y", "z", "w")]
    nets = [net("bus1", "a.n", "b.n", "x.n", "y.n"), net("bus2", "a.s", "b.s", "z.s", "w.s")]
    assert _split_and_rank(problem(syms, nets))[0] == CycleSplit(0, 1, 0)


def test_a_triangle_is_one_cross_link() -> None:
    prob = problem(
        [elem("a"), elem("b"), elem("c")],
        [net("w1", "a.s", "b.n"), net("w2", "b.s", "c.n"), net("w3", "c.s", "a.n")],
    )
    assert _split_and_rank(prob)[0] == CycleSplit(0, 0, 1)


def test_a_junction_merges_its_nets_and_a_rail_leaves_the_graph() -> None:
    syms = [elem("a"), elem("b"), free("j")]
    nets = [net("w1", "a.s", "j.n"), net("w2", "j.s", "b.n"), net("w3", "a.n", "b.s")]
    assert _split_and_rank(problem(syms, nets))[0] == CycleSplit(1, 0, 0)
    rail = net("w3", "a.n", "b.s", rail=Rail(0, "SUPPLY"))
    assert _split_and_rank(problem(syms, [*nets[:2], rail]))[0] == CycleSplit(0, 0, 0)


def test_ties_between_net_ids_follow_natural_order() -> None:
    syms = [elem("a"), elem("b")]
    nets = [net(f"w{i}", "a.n", "b.n") for i in (10, 9, 2)]
    assert cycle_split(problem(syms, nets)) == CycleSplit(2, 0, 0)
