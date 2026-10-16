"""Tests for core/topology_cycles.py: which owners to cut so a y graph has no cycle."""

from __future__ import annotations

import pytest

from fransys_layout.core import natural_key
from fransys_layout.core.topology_cycles import cyclic_parts, y_cycle_cuts
from fransys_layout.core.topology_split import y_cycles

from .cycle_fixtures import ring_problem
from .pipeline_fixtures import flow_of

FIXED = frozenset()


def _cuts(edges: list[tuple[str, str, frozenset[str]]], **cost: int) -> frozenset[str]:
    return y_cycle_cuts(edges, cost, natural_key)


def test_a_two_node_ring_closed_by_one_owned_edge_cuts_that_owner() -> None:
    """The one owned edge of a two-node ring is the owner cut."""
    edges = [("a", "b", FIXED), ("b", "a", frozenset({"n1"}))]
    assert _cuts(edges, n1=1) == frozenset({"n1"})


def test_a_three_node_ring_with_one_owned_edge_cuts_that_owner() -> None:
    """A ring a, b, c with one owned edge is broken by cutting its owner."""
    edges = [
        ("a", "b", FIXED),
        ("b", "c", frozenset({"n1"})),
        ("c", "a", FIXED),
    ]
    assert _cuts(edges, n1=1) == frozenset({"n1"})


def test_the_cheaper_owner_is_cut_first() -> None:
    """Of two owners on one ring, the one losing fewer drivers (cost 1 against 2) is cut."""
    edges = [
        ("a", "b", FIXED),
        ("b", "c", frozenset({"n1"})),
        ("c", "a", frozenset({"n2"})),
    ]
    assert _cuts(edges, n1=1, n2=2) == frozenset({"n1"})


def test_a_cost_tie_is_broken_by_the_natural_key() -> None:
    """Owners n2 and n10 cost the same, and natural order puts n2 first (text order would not)."""
    edges = [
        ("a", "b", FIXED),
        ("b", "c", frozenset({"n10"})),
        ("c", "a", frozenset({"n2"})),
    ]
    assert _cuts(edges, n2=1, n10=1) == frozenset({"n2"})


def test_an_acyclic_graph_cuts_nothing() -> None:
    """A graph with no cycle needs no cut."""
    edges = [("a", "b", FIXED), ("b", "c", frozenset({"n1"})), ("a", "c", FIXED)]
    assert _cuts(edges, n1=1) == frozenset()


def test_the_result_does_not_depend_on_edge_order() -> None:
    """Reversing the edge list gives the same cuts."""
    edges = [
        ("a", "b", FIXED),
        ("b", "c", frozenset({"n10"})),
        ("c", "a", frozenset({"n2"})),
        ("c", "d", frozenset({"n3"})),
        ("d", "c", frozenset({"n3"})),
    ]
    assert _cuts(edges, n2=1, n3=1, n10=1) == _cuts(edges[::-1], n2=1, n3=1, n10=1)


def test_a_cycle_of_fixed_edges_cannot_be_cut() -> None:
    """A cycle with no owned edge raises, naming the nodes of the cycle."""
    edges = [("a", "b", FIXED), ("b", "a", FIXED)]
    with pytest.raises(ValueError, match="no edge that can be cut"):
        _cuts(edges)


def test_an_owner_whose_cut_is_redundant_is_dropped() -> None:
    """n2 is cut first (cheaper), then n1 breaks the second ring, so n2 is redundant and dropped."""
    edges = [
        ("p", "q", frozenset({"n1"})),
        ("q", "p", frozenset({"n2"})),
        ("q", "r", FIXED),
        ("r", "p", FIXED),
    ]
    assert _cuts(edges, n1=2, n2=1) == frozenset({"n1"})


def test_a_self_edge_is_a_cyclic_part() -> None:
    """A node with an edge to itself is a part on its own."""
    assert cyclic_parts([("a", "a")]) == [frozenset({"a"})]


@pytest.mark.parametrize("extra", [0, 1, 2, 3])
def test_stage_one_splits_the_ring_into_a_cross_link(extra: int) -> None:
    """The t01 ring, `extra` parts longer, builds with no finding, one cross link, no y cycle."""
    flow = flow_of(ring_problem(extra))
    assert y_cycles(flow.columns, flow.fans) == []
    assert flow.findings == ()
    assert len(flow.cross_links) == 1
    assert flow.cycle_split.cross_links == 1
