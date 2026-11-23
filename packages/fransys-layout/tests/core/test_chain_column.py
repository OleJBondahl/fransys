"""CHAIN plants: a box-to-box chain is one column, one block, and folds per F2a (layout-0289)."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import pytest
from options_fixtures import core_options

from fransys_layout.core.series_values import Parallel, Series

from .blocks_fixtures import box_sym
from .chain_fixtures import facing_chain, link_box, tall_chain
from .conftest import MARKERS
from .flow_builders import elem, net, problem
from .pipeline_fixtures import blocks_of, cut_of, flow_of, widened_of
from .test_box_blocks import chain_shape

if TYPE_CHECKING:
    from fransys_layout.core.series_values import SeriesPart
    from fransys_layout.core.values import PlacementProblem

NOT_DRAWN_CODES = {
    "NO_BLOCK",
    "NO_CELL",
    "BLOCK_NOT_PLACED",
}


@pytest.mark.rule("CHAIN-COLUMN")
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


@pytest.mark.rule("CHAIN-COLUMN")
def test_a_tall_chain_folds_into_two_columns_with_a_tag_per_net():
    result = _TALL

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


_TALL = cut_of(tall_chain())


def _refused(prob: PlacementProblem, reason: str) -> None:
    """Today's flow (no chain column) and one CHAIN_REFUSED naming the boxes and the reason."""
    flow = flow_of(prob)
    assert not any(c.is_chain for c in flow.columns)
    (found,) = [f for f in flow.findings if f.code == "CHAIN_REFUSED"]
    assert reason in found.text
    assert all(b.id in found.text for b in prob.symbols if b.box is not None)


def test_a_wiring_that_is_no_column_is_refused() -> None:
    """A ring, a box joined to three boxes, a trunk to a third box (h1k2 reaches B3) and pins that all face south are refused."""
    boxes = [link_box(f"R{i}", 1) for i in (1, 2, 3)]
    nets = [net("a", "R1.o1", "R2.i1"), net("b", "R2.o1", "R3.i1"), net("c", "R3.o1", "R1.i1")]
    _refused(problem(boxes, nets), "ring")
    boxes = [link_box("B1", 1, first=True), link_box("B2", 2)]
    boxes += [link_box("B3", 1, last=True), link_box("B4", 1, last=True)]
    nets = [net("a", "B1.o1", "B2.i1"), net("b", "B2.o1", "B3.i1"), net("c", "B2.o2", "B4.i1")]
    _refused(problem(boxes, nets), "three or more boxes")
    prob = facing_chain(3)
    nets = tuple(net("h1k2", "B1.o2", "B2.i2", "B3.i2") if n.id == "h1k2" else n for n in prob.nets)
    _refused(replace(prob, nets=nets), "also wired by net h1k2")
    _refused(chain_shape(), "do not face")


def test_a_refused_chain_is_drawn_unchained_with_a_page() -> None:
    """R348: a refusal is a finding (CHAIN_REFUSED, from stage 1), never a missing layout."""
    result = cut_of(chain_shape())
    assert {f.code for f in result.spec.findings} == set()
    assert len(result.spec.pages) == 1


def test_a_chain_names_its_first_box_by_natural_key_not_by_text() -> None:
    """B2, B9, B10 and B11 run in that order though 'B10' sorts before 'B2' as text."""
    boxes = [link_box(f"B{i}", 1, first=i == 2, last=i == 11) for i in (10, 11, 2, 9)]
    nets = [net("a", "B2.o1", "B9.i1"), net("b", "B9.o1", "B10.i1"), net("c", "B10.o1", "B11.i1")]
    cells = flow_of(problem(boxes, nets)).columns[0].lanes[0].cells
    assert [c.sym for c in cells] == ["B2", "B9", "B10", "B11"]


def test_the_box_columns_option_off_leaves_every_box_to_a_card() -> None:
    flow = flow_of(
        facing_chain(3),
        replace(
            core_options(),
            box_columns=False,
        ),
    )
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
    assert "CHAIN_REFUSED" not in {f.code for f in result.spec.findings}
    assert all(b.seat == "none" for bl in result.blocks for b in bl.blocks)


def test_the_fold_falls_between_two_boxes_and_each_tag_ends_on_the_boxes_beside_it() -> None:
    result = _TALL
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
    result = _TALL
    top, bottom = result.flow.columns
    crossed = {n for hop in tall_chain().nets for n in [hop.id]} - {n for c in (top, bottom) for hop in c.hops for n in hop}
    assert {r.net for r in result.spec.reference_plan} == crossed
    assert len(crossed) == 2


def test_a_fold_is_the_same_twice() -> None:
    assert cut_of(tall_chain()) == cut_of(tall_chain())


def _with_series(prob: PlacementProblem, *parts: SeriesPart) -> PlacementProblem:
    return replace(prob, facts=replace(prob.facts, series=(Series(parts),)))


@pytest.mark.rule("SERIES-PARALLEL")
def test_a_chain_of_boxes_takes_the_order_of_its_series() -> None:
    """A series in signal order keeps the column; the same boxes reversed face the wrong way."""
    for order in (("B1", "B2", "B3"), ("B1", "B3", "B2")):  # the second skips a hop: B1 and B3 share no wire (it raised a KeyError)
        assert [c.sym for c in flow_of(_with_series(facing_chain(3), *order)).columns[0].lanes[0].cells] == ["B1", "B2", "B3"]
    _refused(_with_series(facing_chain(3), "B3", "B2", "B1"), "do not face")


@pytest.mark.rule("SERIES-PARALLEL")
def test_a_parallel_of_boxes_whose_hop_does_not_face_is_refused() -> None:
    """B3 hangs under B2 in the wiring, so it cannot stand beside B1 above B2 (B4: per hop)."""
    _refused(_with_series(facing_chain(3), Parallel(("B1", "B3")), "B2"), "do not face")


def _below_a_box(tail: int = 0) -> PlacementProblem:
    """B1, Parallel(B2, B3), B4, then `tail` more boxes in series: B3 hangs from B1 beside B2, B4 takes both."""
    boxes = [link_box(f"B{n}", 1 if n in (2, 3) else 2, first=n == 1, last=n == 4 + tail) for n in range(1, 5 + tail)]
    nets = [net("a", "B1.o1", "B2.i1"), net("b", "B1.o2", "B3.i1"), net("c", "B2.o1", "B4.i1"), net("d", "B3.o1", "B4.i2")]
    nets += [net(f"t{n}{k}", f"B{n - 1}.o{k}", f"B{n}.i{k}") for n in range(5, 5 + tail) for k in (1, 2)]
    return _with_series(problem(boxes, nets), "B1", Parallel(("B2", "B3")), *(f"B{n}" for n in range(4, 5 + tail)))


@pytest.mark.rule("SERIES-PARALLEL")
@pytest.mark.parametrize("tail", [0, 24])
def test_a_parallel_of_boxes_below_a_box_stands_beside_its_span_and_every_net_is_drawn(tail: int) -> None:
    """R2399, R5: B3 stands level with B2, no CHAIN_REFUSED; its head net b is a cross-link the router draws, also in a tree the cut folds."""
    prob = _below_a_box(tail)
    assert len(flow_of(prob).columns[0].lanes) == 2
    _, routes, findings = widened_of(prob, replace(core_options(), marker_boxes=MARKERS))
    assert not {f.code for f in findings} & {"CONNECTION_NOT_DRAWN", "WIRE_AS_REFERENCE", "CHAIN_REFUSED"}
    assert {"a", "b", "c", "d"} <= {w.net for p in routes.pages for w in p.wires}, "b, the head net, is a wire of its own"


@pytest.mark.rule("SERIES-PARALLEL")
def test_a_parallel_of_boxes_with_no_wire_to_its_neighbour_is_refused() -> None:
    """B1 and B3 share no wire, so B3 cannot stand in parallel with B2 under B1."""
    _refused(_with_series(facing_chain(3), "B1", Parallel(("B2", "B3"))), "share no wire")
