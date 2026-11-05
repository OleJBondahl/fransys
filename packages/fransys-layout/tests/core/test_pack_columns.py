"""Placed columns: the edge flip, which columns hang on a card, and a spilled column."""

import pytest

from fransys_layout.core.flow_values import Cell
from fransys_layout.core.pack import attachments, flip_column, placed_columns
from fransys_layout.core.values import PagePlan

from .pack_fixtures import boxpin_end, card, card_block, column, elem, free_block, lane, row_of

SYMS = {s.id: s for s in (card("box", 2), elem("a"), elem("b"))}


def plan_of(row_columns: tuple[str, ...], blocks: tuple[str, ...]) -> PagePlan:
    return PagePlan(1, "u", (row_of(row_columns, blocks),), groups=())


def test_flip_reverses_a_lane_turns_each_cell_and_negates_offsets() -> None:
    """Cells come out foot first, R0 and R180 swap, pins swap ends, offsets change sign."""
    col = column("c", lane("a", "b", offset=24))
    pc = flip_column(col, flip=True)
    assert pc.flipped
    assert pc.offsets == (-24,)
    assert pc.lanes[0] == (Cell("b", "R180", "s", "n"), Cell("a", "R180", "s", "n"))
    assert flip_column(col, flip=False).lanes == (col.lanes[0].cells,)
    again = flip_column(column("c", lane("a", "b")), flip=True).lanes[0]
    assert tuple(Cell(c.sym, "R180" if c.orient == "R0" else "R0", c.bottom_pin, c.top_pin) for c in reversed(again)) == col.lanes[0].cells


@pytest.mark.parametrize(("end", "edges"), [("head", ("N", "S")), ("foot", ("S", "N"))])
def test_a_column_whose_end_pin_edge_faces_away_is_flipped(end: str, edges: tuple[str, str]) -> None:
    """The flip reads the end (KI-397): a head end on a north edge or a foot end on a south edge turns the column."""
    cols = {
        "c1": column("c1", lane("a"), **{end: boxpin_end("box", "p1")}),
        "c2": column("c2", lane("b"), **{end: boxpin_end("box", "p2")}),
    }
    block = card_block("box", ("c1", "c2"), (("p1", edges[0]), ("p2", edges[1])))
    blocks = {block.id: block}
    attach = attachments(tuple(cols.values()), blocks)
    assert attach == {"c1": ("box", "p1", 0), "c2": ("box", "p2", 0)}
    out = placed_columns(plan_of(("c1", "c2"), (block.id,)), cols, blocks, attach, SYMS)
    assert out["c1"].flipped
    assert not out["c2"].flipped


def test_a_spilled_column_places_as_a_free_column() -> None:
    """A box-pin end the card block does not list is not attached and is never flipped."""
    cols = {"c1": column("c1", lane("a"), head=boxpin_end("box", "p1"))}
    card_b = card_block("box", (), (("p1", "N"),))
    free_b = free_block("free:1", ("c1",))
    blocks = {card_b.id: card_b, free_b.id: free_b}
    assert attachments(tuple(cols.values()), blocks) == {}
    out = placed_columns(plan_of(("c1",), (card_b.id, free_b.id)), cols, blocks, {}, SYMS)
    assert not out["c1"].flipped


def test_a_card_is_found_by_kind_not_by_its_id() -> None:
    """Block ids are opaque: a card block with a plain id still holds its columns."""
    cols = {"c1": column("c1", lane("a"), head=boxpin_end("box", "p1"))}
    block = card_block("box", ("c1",), (("p1", "S"),), "zzz")
    assert attachments(tuple(cols.values()), {block.id: block}) == {"c1": ("box", "p1", 0)}


def test_a_column_takes_the_edge_of_its_own_box_when_another_card_shares_the_pin_id() -> None:
    """Two cards in one row with the same pin id on opposite edges: each foot-attached column reads its own box (WMN class 3)."""
    cols = {"c1": column("c1", lane("a"), foot=boxpin_end("k1", "p1")), "c2": column("c2", lane("b"), foot=boxpin_end("k2", "p1"))}
    k1, k2 = card_block("k1", ("c1",), (("p1", "N"),)), card_block("k2", ("c2",), (("p1", "S"),))
    blocks = {k1.id: k1, k2.id: k2}
    syms = {s.id: s for s in (card("k1", 1), card("k2", 1), elem("a"), elem("b"))}
    attach = attachments(tuple(cols.values()), blocks)
    out = placed_columns(plan_of(("c1", "c2"), (k1.id, k2.id)), cols, blocks, attach, syms)
    assert (out["c1"].flipped, out["c2"].flipped) == (False, True)
