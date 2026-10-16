"""Two known gaps of the cut, planted as strict xfail: each flips to a pass when its fix lands.

Both are the README's "Known gaps" of the placement draft and are left unfixed by layout-0280.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from fransys_layout.core import Hints, Options, PlacementProblem, order_blocks
from fransys_layout.core.blocks import assign_blocks
from fransys_layout.core.cut import cut_pages
from fransys_layout.core.values import Cell, Column, CycleSplit, End, FlowGraph, Lane

from .blocks_fixtures import AREA
from .cut_fixtures import cut_of, elem, net


@pytest.mark.xfail(
    strict=True,
    reason="Multi-lane tall columns are not split: a two-lane column taller than the page stays",
)
def test_a_two_lane_column_taller_than_the_page_is_cut_into_columns() -> None:
    """Two lanes of twelve 96 G cells make a column 1240 G tall on an 822 G page."""
    ids = [f"k{n}{i:02d}" for n in (0, 1) for i in range(12)]
    syms = tuple(elem(i, 40, 96) for i in ids)
    lanes = tuple(
        Lane(tuple(Cell(i, "R0", "n", "s") for i in ids[12 * n : 12 * n + 12]), 48 * n)
        for n in (0, 1)
    )
    col = Column("c", lanes, (End("open"), End("open")), (End("open"), End("open")), 1240, 88)
    flow = FlowGraph((col,), (), (), (), CycleSplit(0, 0, 0), ())
    prob = PlacementProblem(AREA, syms, ())
    lists = order_blocks(assign_blocks(flow, prob, Options()), flow, Options())
    result = cut_pages(lists, flow, prob, Options())
    assert len(result.flow.columns) > 1


@pytest.mark.xfail(
    strict=True, reason="P6 is strict: the cut spreads a row group of three symbols over two rows"
)
def test_a_row_group_the_cut_would_spread_over_two_rows_stays_in_one() -> None:
    """Column x then three columns of one row group: the row break falls inside the group."""
    members = [replace(elem(f"r{i}", 300), row_group="R1") for i in (1, 2, 3)]
    syms = [elem("x0", 500, 32, "G0"), elem("x1", 500, 32, "G0"), *members]
    syms += [elem(f"s{i}", 300, 32, "G1") for i in (1, 2, 3)]
    nets = [net("x", "x0.s", "x1.n")]
    nets += [net(f"m{i}", f"r{i}.s", f"s{i}.n") for i in (1, 2, 3)]
    result = cut_of(syms, nets, hints=Hints(group_order=("G0", "G1")))
    row_of = {c: n for p in result.spec.pages for n, r in enumerate(p.rows) for c in r.columns}
    assert len({row_of[f"c:r{i}"] for i in (1, 2, 3)}) == 1
