"""Tests for core/topology_cycles.py: which owners to cut so a y graph has no cycle."""

from __future__ import annotations

import pytest

from fransys_layout.core import CoreError, natural_key
from fransys_layout.core.topology_cycles import CycleCutError, cyclic_parts, y_cycle_cuts
from fransys_layout.core.topology_split import y_cycles

from .cycle_fixtures import ring_problem
from .pipeline_fixtures import flow_of

FIXED = frozenset()


def _cuts(edges: list[tuple[str, str, frozenset[str]]], **cost: int) -> frozenset[str]:
    keys = {n: natural_key(n) for a, b, owners in edges for n in (a, b, *owners)}
    return y_cycle_cuts(edges, cost, keys)


@pytest.mark.parametrize(
    ("edges", "cost", "cut"),
    [
        ([("a", "b", FIXED), ("b", "a", frozenset({"n1"}))], {"n1": 1}, {"n1"}),  # the one owned edge of a two-node ring
        ([("a", "b", FIXED), ("b", "c", frozenset({"n1"})), ("c", "a", FIXED)], {"n1": 1}, {"n1"}),  # a ring of three, one owned edge
        ([("a", "b", FIXED), ("b", "c", frozenset({"n1"})), ("c", "a", frozenset({"n2"}))], {"n1": 1, "n2": 2}, {"n1"}),  # cost 1 against 2
        (
            [("a", "b", FIXED), ("b", "c", frozenset({"n10"})), ("c", "a", frozenset({"n2"}))],
            {"n2": 1, "n10": 1},
            {"n2"},
        ),  # tie: natural order, not text
    ],
    ids=["two-node-ring", "three-node-ring", "cheaper-owner-first", "tie-by-natural-key"],
)
def test_the_owner_that_breaks_a_ring_is_cut(edges: list[tuple[str, str, frozenset[str]]], cost: dict[str, int], cut: set[str]) -> None:
    """A ring is broken at its one owned edge, else at the cheaper owner, else at the first by natural order."""
    assert _cuts(edges, **cost) == frozenset(cut)


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
    """A cycle with no owned edge raises a CoreError naming the nodes in natural-key order."""
    edges = [("c:10", "c:9", FIXED), ("c:9", "c:10", FIXED), ("x", "y", frozenset({"n1"}))]
    with pytest.raises(CycleCutError, match=r"through c:9, c:10 has no edge that can be cut") as e:
        _cuts(edges)
    assert isinstance(e.value, CoreError)


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
