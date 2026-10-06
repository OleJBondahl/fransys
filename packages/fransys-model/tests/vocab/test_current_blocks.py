"""`vocab.current_blocks.blocks`: the biconnected blocks of a multigraph, by edge index.

Every expected value is worked by hand from the shape of the graph (vertices are letters).
"""

import sys
from typing import TYPE_CHECKING

import fransys_model.vocab.current_blocks as module
from fransys_model.vocab.current_blocks import blocks

if TYPE_CHECKING:
    from types import FrameType


def _sets(*edges: tuple[str, str]) -> set[frozenset[int]]:
    return set(blocks(edges))


def test_a_graph_without_edges_has_no_block() -> None:
    assert blocks([]) == ()


def test_a_ring_is_one_block() -> None:
    assert _sets(("a", "b"), ("b", "c"), ("c", "a")) == {frozenset({0, 1, 2})}


def test_two_parallel_edges_are_a_block_and_three_are_one_block() -> None:
    assert _sets(("a", "b"), ("b", "a")) == {frozenset({0, 1})}
    assert _sets(("a", "b"), ("a", "b"), ("b", "a")) == {frozenset({0, 1, 2})}


def test_a_bridge_is_a_block_of_one_edge() -> None:
    assert _sets(("a", "b")) == {frozenset({0})}
    assert _sets(("a", "b"), ("b", "c")) == {frozenset({0}), frozenset({1})}


def test_a_triangle_with_a_tail_is_two_blocks() -> None:
    edges = (("a", "b"), ("b", "c"), ("c", "a"), ("c", "d"))
    assert blocks(edges) == (frozenset({0, 1, 2}), frozenset({3}))


def test_a_figure_eight_is_two_blocks_at_the_cut_vertex() -> None:
    edges = (("a", "b"), ("b", "c"), ("c", "a"), ("c", "d"), ("d", "e"), ("e", "c"))
    assert _sets(*edges) == {frozenset({0, 1, 2}), frozenset({3, 4, 5})}


def test_a_theta_graph_is_one_block() -> None:
    """Three paths between a and b: a - b, a - c - b and a - d - e - b."""
    edges = (("a", "b"), ("a", "c"), ("c", "b"), ("a", "d"), ("d", "e"), ("e", "b"))
    assert _sets(*edges) == {frozenset(range(6))}


def test_a_cut_vertex_between_a_ring_and_a_parallel_pair() -> None:
    edges = (("a", "b"), ("b", "c"), ("c", "a"), ("c", "d"), ("d", "c"))
    assert _sets(*edges) == {frozenset({0, 1, 2}), frozenset({3, 4})}


def test_a_parallel_pair_inside_a_ring_stays_one_block() -> None:
    edges = (("a", "b"), ("a", "b"), ("b", "c"), ("c", "a"))
    assert _sets(*edges) == {frozenset({0, 1, 2, 3})}


def test_disconnected_parts_are_separate_blocks() -> None:
    assert _sets(("a", "b"), ("b", "a"), ("x", "y")) == {frozenset({0, 1}), frozenset({2})}


def test_the_result_does_not_depend_on_the_order_of_the_edges() -> None:
    edges = [("a", "b"), ("b", "c"), ("c", "a"), ("c", "d")]
    forward = {frozenset(edges[i] for i in block) for block in blocks(edges)}
    backward = {frozenset(edges[::-1][i] for i in block) for block in blocks(edges[::-1])}
    assert forward == backward == {frozenset(edges[:3]), frozenset(edges[3:])}


def _lines_run_by_blocks(edges: list[tuple[int, int]]) -> int:
    """Source lines `blocks` executes on `edges`: an operation count, not a clock."""
    lines = 0

    def trace(frame: FrameType, event: str, _arg: object):
        nonlocal lines
        if frame.f_code.co_filename != module.__file__:
            return None
        lines += event == "line"
        return trace

    previous = sys.gettrace()
    sys.settrace(trace)
    try:
        blocks(edges)
    finally:
        sys.settrace(previous)
    return lines


def test_a_long_path_of_bridges_is_found_in_linear_time() -> None:
    """Each bridge is popped from the top of the edge stack: 28 lines per bridge (measured), where
    scanning the stack from its bottom would cost the square of the length."""
    size = 2000
    edges = [(n, n + 1) for n in range(size)]
    assert _lines_run_by_blocks(edges) <= 30 * size
    assert blocks(edges) == tuple(frozenset({n}) for n in range(size))


def test_a_long_string_does_not_recurse() -> None:
    """A path of 5000 edges closed into a ring is one block (a recursive search would overflow)."""
    size = 5000
    edges = [(n, (n + 1) % size) for n in range(size)]
    assert blocks(edges) == (frozenset(range(size)),)
