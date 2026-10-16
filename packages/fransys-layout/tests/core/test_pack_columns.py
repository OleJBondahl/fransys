"""Placed columns: the edge flip, which columns hang on a card, and a spilled column."""

from fransys_layout.core.pack import attachments, flip_column, placed_columns
from fransys_layout.core.values import Cell, PagePlan

from .pack_fixtures import boxpin_end, card, card_block, column, elem, free_block, lane, row_of

SYMS = {s.id: s for s in (card("box", 2), elem("a"), elem("b"))}


def plan_of(row_columns: tuple[str, ...], blocks: tuple[str, ...]) -> PagePlan:
    return PagePlan(1, "u", (row_of(row_columns, blocks),), forced_end=False, groups=())


def test_flip_reverses_a_lane_turns_each_cell_and_negates_offsets() -> None:
    """Cells come out foot first, R0 and R180 swap, pins swap ends, offsets change sign."""
    col = column("c", lane("a", "b", offset=24))
    pc = flip_column(col, flip=True)
    assert pc.flipped
    assert pc.offsets == (-24,)
    assert pc.lanes[0] == (Cell("b", "R180", "s", "n"), Cell("a", "R180", "s", "n"))
    assert flip_column(col, flip=False).lanes == (col.lanes[0].cells,)
    again = flip_column(column("c", lane("a", "b")), flip=True).lanes[0]
    assert (
        tuple(
            Cell(c.sym, "R180" if c.orient == "R0" else "R0", c.bottom_pin, c.top_pin)
            for c in reversed(again)
        )
        == col.lanes[0].cells
    )


def test_an_attached_column_on_the_other_edge_is_flipped() -> None:
    """The pin faces south; the block puts p1 on its north edge, so its column stands flipped."""
    cols = {
        "c1": column("c1", lane("a"), head=boxpin_end("box", "p1")),
        "c2": column("c2", lane("b"), head=boxpin_end("box", "p2")),
    }
    block = card_block("box", ("c1", "c2"), (("p1", "N"), ("p2", "S")))
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
