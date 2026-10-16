"""CHAIN plants: a box-to-box chain is one column, one block, and folds per F2a (layout-0289)."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from fransys_layout.core.values import Options

from .blocks_fixtures import box_sym
from .chain_fixtures import facing_chain, link_box, tall_chain
from .flow_builders import elem, net, problem
from .pipeline_fixtures import blocks_of, cut_of, flow_of
from .test_box_blocks import chain_shape

if TYPE_CHECKING:
    from fransys_layout.core.values import PlacementProblem

NOT_DRAWN_CODES = {
    "OUT_OF_CONTENT_BOX",
    "PAGE_OVERFULL",
    "NO_BLOCK",
    "NO_CELL",
    "BLOCK_NOT_PLACED",
    "CHAIN_NOT_DRAWN",
}


def test_a_chain_of_boxes_is_one_column_in_natural_key_order():
    flow = flow_of(facing_chain(3))

    assert len(flow.columns) == 1
    assert flow.fans == ()
    assert [c.sym for c in flow.columns[0].lanes[0].cells] == ["B1", "B2", "B3"]
    assert flow.columns[0].hops == (("h1k1", "h1k2"), ("h2k1", "h2k2"))


def test_a_chain_is_one_block_that_is_no_card():
    lists = blocks_of(facing_chain(3))
    blocks = [b for bl in lists for b in bl.blocks]

    assert len(blocks) == 1
    assert len(blocks[0].columns) == 1
    assert not blocks[0].is_card
    assert blocks[0].anchor is None


def test_a_tall_chain_folds_into_two_columns_with_a_tag_per_net():
    result = cut_of(tall_chain())

    assert len(result.flow.columns) == 2
    refs = result.spec.reference_plan
    assert len(refs) == 2
    assert all(ref.kind == "tag" and len(ref.ends) == 2 for ref in refs)
    nets = {ref.net for ref in refs}
    hops = {net.split("k")[0] for net in nets}
    assert len(nets) == 2
    assert len(hops) == 1
    hop = hops.pop()
    assert nets == {f"{hop}k1", f"{hop}k2"}
    assert len(result.spec.pages) == 1
    assert not {f.code for f in result.spec.findings} & NOT_DRAWN_CODES


def _refused(prob: PlacementProblem, reason: str) -> None:
    """Today's flow (no chain column) and one CHAIN_REFUSED naming the boxes and the reason."""
    flow = flow_of(prob)
    assert not any(c.is_chain for c in flow.columns)
    (found,) = [f for f in flow.findings if f.code == "CHAIN_REFUSED"]
    assert reason in found.text
    assert all(b.id in found.text for b in prob.symbols if b.box is not None)


def test_a_ring_of_boxes_is_refused_not_dropped() -> None:
    boxes = [link_box(f"R{i}", 1) for i in (1, 2, 3)]
    nets = [net("a", "R1.o1", "R2.i1"), net("b", "R2.o1", "R3.i1"), net("c", "R3.o1", "R1.i1")]
    _refused(problem(boxes, nets), "ring")


def test_a_box_joined_to_three_boxes_is_refused() -> None:
    boxes = [link_box("B1", 1, first=True), link_box("B2", 2)]
    boxes += [link_box("B3", 1, last=True), link_box("B4", 1, last=True)]
    nets = [net("a", "B1.o1", "B2.i1"), net("b", "B2.o1", "B3.i1"), net("c", "B2.o2", "B4.i1")]
    _refused(problem(boxes, nets), "three or more boxes")


def test_a_box_with_a_trunk_to_a_third_box_is_refused() -> None:
    """The net h1k2 reaches B3 too, so B2 is wired by a trunk and is no chain box."""
    prob = facing_chain(3)
    nets = tuple(net("h1k2", "B1.o2", "B2.i2", "B3.i2") if n.id == "h1k2" else n for n in prob.nets)
    _refused(replace(prob, nets=nets), "also wired by net h1k2")


def test_boxes_whose_pins_do_not_face_are_refused() -> None:
    """chain_shape's pins all face south: the wires would run up the box."""
    _refused(chain_shape(), "do not face")


def test_a_refused_chain_is_still_reported_as_not_drawn() -> None:
    result = cut_of(chain_shape())
    assert {f.code for f in result.spec.findings} == {"CHAIN_NOT_DRAWN"}
    assert result.spec.pages == ()


def test_a_chain_names_its_first_box_by_natural_key_not_by_text() -> None:
    """B2, B9, B10 and B11 run in that order though 'B10' sorts before 'B2' as text."""
    boxes = [link_box(f"B{i}", 1, first=i == 2, last=i == 11) for i in (10, 11, 2, 9)]
    nets = [net("a", "B2.o1", "B9.i1"), net("b", "B9.o1", "B10.i1"), net("c", "B10.o1", "B11.i1")]
    cells = flow_of(problem(boxes, nets)).columns[0].lanes[0].cells
    assert [c.sym for c in cells] == ["B2", "B9", "B10", "B11"]


def test_the_box_columns_option_off_leaves_every_box_to_a_card() -> None:
    flow = flow_of(facing_chain(3), replace(Options(), box_columns=False))
    assert not any(c.is_chain for c in flow.columns)
    assert len(flow.fans) == 4
    assert [f.code for f in flow.findings] == []


def _chain_beside_a_card() -> PlacementProblem:
    """B1..B3 chain, and a card K with one coil E on its pin."""
    chain_prob = facing_chain(3)
    card = box_sym("K", None, 1)
    coil = elem("E")
    nets = (*chain_prob.nets, net("kc", "K.p1", "E.n"))
    return problem([*chain_prob.symbols, card, coil], list(nets))


def test_a_card_beside_a_chain_keeps_its_block_and_the_chain_is_one_block() -> None:
    blocks = {b.id: b for bl in blocks_of(_chain_beside_a_card()) for b in bl.blocks}
    cards = [b for b in blocks.values() if b.is_card]
    assert [(b.anchor, b.columns) for b in cards] == [("K", ("c:E",))]
    (chain_block,) = [b for b in blocks.values() if not b.is_card and "c:B1" in b.columns]
    assert chain_block.columns == ("c:B1",)


def test_a_chain_box_reaches_a_row_inside_its_block_and_no_bare_seat_is_made() -> None:
    result = cut_of(_chain_beside_a_card())
    rows = [r for p in result.spec.pages for r in p.rows]
    assert any(r.columns == ("c:B1",) or "c:B1" in r.columns for r in rows)
    assert "CHAIN_NOT_DRAWN" not in {f.code for f in result.spec.findings}
    assert all(b.seat == "none" for bl in result.blocks for b in bl.blocks)


def test_the_fold_falls_between_two_boxes_and_each_tag_ends_on_the_boxes_beside_it() -> None:
    result = cut_of(tall_chain())
    top, bottom = result.flow.columns
    last, first = top.lanes[0].cells[-1].sym, bottom.lanes[0].cells[0].sym
    assert (len(top.lanes[0].cells) + len(bottom.lanes[0].cells), top.is_chain) == (24, True)
    assert len(top.hops) == len(top.lanes[0].cells) - 1
    assert len(bottom.hops) == len(bottom.lanes[0].cells) - 1
    for ref in result.spec.reference_plan:
        assert [(e.column, e.pin.sym) for e in ref.ends if e.pin] == [
            (top.id, last),
            (bottom.id, first),
        ]


def test_every_net_of_the_fold_hop_is_tagged_and_the_others_are_not() -> None:
    """No Ref is lost: 23 hops of two nets, and only the fold hop's two nets are tags."""
    result = cut_of(tall_chain())
    top, bottom = result.flow.columns
    crossed = {n for hop in tall_chain().nets for n in [hop.id]} - {
        n for c in (top, bottom) for hop in c.hops for n in hop
    }
    assert {r.net for r in result.spec.reference_plan} == crossed
    assert len(crossed) == 2


def test_a_fold_is_the_same_twice() -> None:
    assert cut_of(tall_chain()) == cut_of(tall_chain())
