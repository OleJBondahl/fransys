"""P1-4B plants: every drawn box is held by exactly one block (layout-0283).

K1's shape is a box wired to a trunk by its pin alone; w10's is boxes joined box to box. Both
leave the box in no card, so stage 2 gives it a free single-symbol block.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fransys_layout.core.blocks_check import box_findings

from .blocks_fixtures import box_sym
from .flow_builders import net, problem
from .pipeline_fixtures import blocks_of, flow_of
from .test_hub_cells import TERMINALS, hub_shape

if TYPE_CHECKING:
    from fransys_layout.core.values import Block, PlacementProblem


def chain_shape() -> PlacementProblem:
    """Three boxes joined by box-to-box nets."""
    boxes = [box_sym(f"A{i}", "PLC", 2) for i in (1, 2, 3)]
    return problem(boxes, [net("n1", "A1.p1", "A2.p1"), net("n2", "A2.p2", "A3.p1")])


def _blocks(prob: PlacementProblem) -> list[Block]:
    return [b for bl in blocks_of(prob) for b in bl.blocks]


def _held_by(prob: PlacementProblem, sym: str) -> int:
    flow = flow_of(prob)
    cols = {c.id: c for c in flow.columns}
    return sum(
        1
        for b in _blocks(prob)
        if b.anchor == sym
        or any(c.sym == sym for col in b.columns for ln in cols[col].lanes for c in ln.cells)
    )


def test_trunk_wired_box_is_in_one_block_and_each_terminal_in_one() -> None:
    prob = hub_shape()
    for sym in ("K", *TERMINALS):
        assert _held_by(prob, sym) == 1, sym
    assert [b.anchor for b in _blocks(prob) if b.anchor == "K"] == ["K"]


def test_a_chain_of_boxes_has_each_box_in_exactly_one_block() -> None:
    prob = chain_shape()
    assert set(flow_of(prob).drawn) == {"A1", "A2", "A3"}
    for sym in ("A1", "A2", "A3"):
        assert _held_by(prob, sym) == 1, sym


def test_no_block_names_a_box_held_by_no_block() -> None:
    prob = hub_shape()
    syms = {s.id: s for s in prob.symbols}
    flow = flow_of(prob)
    kept = [b for b in _blocks(prob) if b.anchor != "K"]
    found = box_findings(flow.drawn, syms, kept)
    assert [(f.code, f.subject) for f in found] == [("NO_BLOCK", "K")]


def test_a_box_held_by_two_blocks_gives_one_no_block_finding_naming_it() -> None:
    prob = hub_shape()
    syms = {s.id: s for s in prob.symbols}
    blocks = _blocks(prob)
    twice = [*blocks, *(b for b in blocks if b.anchor == "K")]
    found = box_findings(flow_of(prob).drawn, syms, twice)
    assert [(f.code, f.subject) for f in found] == [("NO_BLOCK", "K")]


def test_the_assembled_lists_carry_no_no_block_finding_when_every_box_is_held() -> None:
    for prob in (hub_shape(), chain_shape()):
        assert [f for bl in blocks_of(prob) for f in bl.findings if f.code == "NO_BLOCK"] == []
