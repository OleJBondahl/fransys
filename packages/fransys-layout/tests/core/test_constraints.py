"""The difference-constraint graph: longest path, refusals, and the heap pop count."""

from __future__ import annotations

from typing import Any

import pytest

from fransys_layout.core import constraints
from fransys_layout.core.constraints import Graph


@pytest.mark.parametrize(
    ("first", "second", "expected"),
    [
        (8, 8, (0, 8, 16)),
        pytest.param(13, -3, (0, 13, 10), marks=pytest.mark.rule("ROW-ON-GRID")),
    ],
)
def test_longest_path_keeps_each_distance_as_given(first: int, second: int, expected: tuple[int, int, int]) -> None:
    """after(a, b, first) and after(b, c, second) put c at the sum, a at its default 0; R1693: the graph rounds nothing (13, -3 give 0, 13, 10)."""
    g = Graph()
    g.after("a", "b", first)
    g.after("b", "c", second)
    y = g.solve()
    assert y is not None
    assert (y["a"], y["b"], y["c"]) == expected


def test_equal_and_after_conflict_gives_no_solution() -> None:
    """equal(a, c, 4) against the chain a -> b -> c of 8s has no answer."""
    g = Graph()
    g.after("a", "b", 8)
    g.after("b", "c", 8)
    g.equal("a", "c", 4)
    assert g.solve() is None


def test_no_edges_puts_every_node_at_zero() -> None:
    """Nodes that no edge names all sit at the origin's 0."""
    g = Graph()
    g.add("p")
    g.add("q")
    assert g.solve() == {"@origin": 0, "p": 0, "q": 0}


@pytest.mark.parametrize("weight", [0, 8])
def test_a_cycle_has_no_solution_even_at_zero_weight(weight: int) -> None:
    """after(a, b, w) and after(b, a, w) form a cycle, and a zero-weight cycle is refused too."""
    g = Graph()
    g.after("a", "b", weight)
    g.after("b", "a", weight)
    assert g.solve() is None


def test_a_solve_of_3000_chained_nodes_pops_the_heap_once_per_node(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A 3000-node chain is solved with at most one heap pop per node, and the answer is right."""
    pops = 0
    real_pop = constraints.heapq.heappop

    def counting_pop(heap: list[tuple[tuple[Any, ...], str]]) -> tuple[tuple[Any, ...], str]:
        nonlocal pops
        pops += 1
        return real_pop(heap)

    monkeypatch.setattr(constraints.heapq, "heappop", counting_pop)
    g = Graph()
    for i in range(3000):
        g.after(f"n{i}", f"n{i + 1}", 8)
    y = g.solve()
    assert y is not None
    assert y["n3000"] == 24000
    assert pops <= len(g.nodes)


def test_solve_has_no_answer_when_a_class_holds_an_after_edge_closer_than_asked() -> None:
    """b stands 10 under a but the edge asks 20: no answer, as for a cycle."""
    g = Graph()
    g.equal("a", "b", 10)
    g.after("a", "b", 20)
    assert g.solve() is None


def test_solve_accepts_an_after_edge_inside_a_class_that_the_offsets_satisfy() -> None:
    """An in-class edge the offsets satisfy (10, and -10 back) solves with b 10 under a."""
    g = Graph()
    g.equal("a", "b", 10)
    g.after("a", "b", 10)
    g.after("b", "a", -10)
    y = g.solve()
    assert y is not None
    assert y["b"] - y["a"] == 10
