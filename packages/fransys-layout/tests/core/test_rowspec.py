"""one_row: the throwaway one-row page that stages 2 and 4 measure with row_width."""

from __future__ import annotations

from fransys_layout.core.geometry import column_extent
from fransys_layout.core.pack import PlacedColumn, attachments
from fransys_layout.core.pack_row import RowSpec, row_width
from fransys_layout.core.pack_sep import separation
from fransys_layout.core.rowspec import one_row
from fransys_layout.core.values import (
    Box,
    CycleSplit,
    FlowGraph,
    Lane,
    Options,
    PlacementProblem,
    Sym,
)

from .blocks_fixtures import AREA
from .pack_fixtures import boxpin_end, card, card_block, column, elem, free_block, lane, placed

NONE: frozenset[str] = frozenset()


def world(syms: list[Sym], cols: list) -> tuple[FlowGraph, PlacementProblem]:
    flow = FlowGraph(tuple(cols), (), (), (), CycleSplit(0, 0, 0), ())
    return flow, PlacementProblem(AREA, tuple(syms), ())


def test_a_lone_column_measures_its_extent() -> None:
    syms = [elem("a", footprint=Box(-20, -16, 50, 32))]
    cols = [column("c1", lane("a"))]
    flow, prob = world(syms, cols)
    spec = one_row(("c1",), (free_block("f", ("c1",)),), flow, prob, Options())
    lo, hi = column_extent(spec.syms, (Lane(spec.pcs["c1"].lanes[0], 0),), NONE)
    assert row_width(spec) == hi - lo == 50


def test_two_free_columns_are_the_first_reach_plus_separation_plus_the_second_reach() -> None:
    syms = [elem("a", footprint=Box(-20, -16, 50, 32)), elem("b", footprint=Box(-9, -16, 40, 32))]
    cols = [column("c1", lane("a")), column("c2", lane("b"))]
    flow, prob = world(syms, cols)
    options = Options()
    spec = one_row(("c1", "c2"), (free_block("f", ("c1", "c2")),), flow, prob, options)
    sep = separation(spec.pcs["c1"], spec.pcs["c2"], spec.syms, NONE, options)
    assert row_width(spec) == 20 + sep + 31


def test_a_card_block_measures_as_the_hand_built_row_spec() -> None:
    syms = [card("box", 3), elem("a", body=Box(-2, -16, 4, 32))]
    cols = [column(f"c{i}", lane("a"), head=boxpin_end("box", f"p{i}")) for i in (1, 2, 3)]
    names = tuple(c.id for c in cols)
    block = card_block("box", names, tuple((f"p{i}", "S") for i in (1, 2, 3)))
    flow, prob = world(syms, cols)
    options = Options()
    got = one_row(names, (block,), flow, prob, options)
    pcs = {c: placed(c, "a") for c in names}
    attach = attachments(tuple(cols), {block.id: block})
    want = RowSpec(names, (block,), pcs, {s.id: s for s in syms}, NONE, options, attach)
    assert row_width(got) == row_width(want)
    assert got.attach == attach


def test_a_column_attached_on_the_far_edge_is_flipped() -> None:
    syms = [card("box", 2), elem("a")]
    cols = [column(f"c{i}", lane("a"), head=boxpin_end("box", f"p{i}")) for i in (1, 2)]
    block = card_block("box", ("c1", "c2"), (("p1", "N"), ("p2", "S")))
    flow, prob = world(syms, cols)
    spec = one_row(("c1", "c2"), (block,), flow, prob, Options())
    assert isinstance(spec.pcs["c1"], PlacedColumn)
    assert (spec.pcs["c1"].flipped, spec.pcs["c2"].flipped) == (True, False)
