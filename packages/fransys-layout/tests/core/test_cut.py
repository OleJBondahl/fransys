"""`cut_pages` as a whole: the page groups, the flow it hands on, and determinism."""

from __future__ import annotations

from dataclasses import replace

from fransys_layout.core import Hints, Options, PlacementProblem, order_blocks
from fransys_layout.core.cut import cut_pages
from fransys_layout.core.values import Block, BlockList, CycleSplit, FlowGraph

from .blocks_fixtures import AREA, column, sym
from .conftest import MARKER_BOX
from .cut_fixtures import chain, cut_of, elem, net
from .pack_fixtures import free_block
from .pipeline_fixtures import blocks_of, flow_of


def _block(block_id: str, col: str, group: str | None) -> Block:
    return replace(free_block(block_id, (col,)), group=group, short=True, height_est=32)


def test_page_plan_groups_list_the_groups_of_the_page_in_order() -> None:
    """Blocks of g2, g1, a group-less one and g2 again on one page: ("g2", "g1")."""
    groups = ("g2", "g1", None, "g2")
    syms = [sym(f"s{i}", g) for i, g in enumerate(groups, 1)]
    cols = [column(f"c{i}", f"s{i}") for i in range(1, 5)]
    blocks = tuple(_block(f"b{i}", f"c{i}", g) for i, g in enumerate(groups, 1))
    flow = FlowGraph(tuple(cols), (), (), (), CycleSplit(0, 0, 0), ())
    prob = PlacementProblem(AREA, tuple(syms), ())
    result = cut_pages((BlockList("u", blocks),), flow, prob, Options(marker=MARKER_BOX))
    (page,) = result.spec.pages
    assert page.groups == ("g2", "g1")


def test_the_cut_result_carries_the_flow_after_tall_splits() -> None:
    ids = [f"k{i:02d}" for i in range(12)]
    result = cut_of([elem(i, 40, 96) for i in ids], chain(ids))
    assert [c.id for c in result.flow.columns] == ["c:k00#a", "c:k00#b"]
    assert result.blocks[0].blocks[0].columns == ("c:k00#a", "c:k00#b")
    small = [elem(i, 40, 32) for i in ids]
    prob = PlacementProblem(AREA, tuple(small), tuple(chain(ids)))
    flow = flow_of(prob)
    lists = order_blocks(blocks_of(prob), flow, Options(marker=MARKER_BOX))
    assert (
        cut_pages(lists, flow, prob, Options(marker=MARKER_BOX)).flow is flow
    )  # nothing tall: the flow is kept


def test_the_cut_is_deterministic() -> None:
    legs = [f"l{i:02d}" for i in range(12)]
    syms = [elem("src", 150, 32, "G0"), *(elem(leg, 150, 32, "G1") for leg in legs)]
    nets = [net("bus", "src.s", *(f"{leg}.n" for leg in legs))]
    hints = Hints(group_order=("G0", "G1"))
    assert cut_of(syms, nets, hints=hints) == cut_of(syms, nets, hints=hints)
