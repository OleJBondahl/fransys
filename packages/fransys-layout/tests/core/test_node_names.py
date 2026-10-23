"""The pack-row node names: each writer pairs with its predicate, prefixes stay apart."""

from options_fixtures import core_options

from fransys_layout.core.constraints import ORIGIN
from fransys_layout.core.node_names import (
    BOX,
    COL,
    HIGH,
    LOW,
    PIN,
    SLOT,
    box_node,
    box_y_node,
    col_node,
    pin_node,
    slot_node,
)
from fransys_layout.core.pack import PlacedColumn, attachments
from fransys_layout.core.pack_row import RowSpec, solve_row

from .pack_fixtures import boxpin_end, card, card_block, column, elem, lane


def is_slot_node(name: str) -> bool:
    return name.startswith(SLOT)


def is_box_node(name: str) -> bool:
    return name.startswith(BOX)


def is_pin_node(name: str) -> bool:
    return name.startswith(PIN)


def is_col_node(name: str) -> bool:
    return name.startswith(COL)


PREDICATES = (is_slot_node, is_box_node, is_pin_node, is_col_node)


def test_each_writer_satisfies_only_its_own_predicate() -> None:
    """A name from one writer is read by one predicate; box_node and box_y_node share one."""
    names = (
        (slot_node("b", LOW), is_slot_node),
        (box_node("b", HIGH), is_box_node),
        (box_y_node("b"), is_box_node),
        (pin_node("b", "p1"), is_pin_node),
        (col_node("c"), is_col_node),
    )
    for name, predicate in names:
        assert [p for p in PREDICATES if p(name)] == [predicate]


def test_names_keep_their_ids_and_the_two_ends_differ() -> None:
    """The id is part of the name, so two ids or the two ends never give one name."""
    assert slot_node("a", LOW) != slot_node("a", HIGH)
    assert box_node("a", LOW) != box_node("b", LOW)
    assert pin_node("a", "1") != pin_node("a", "2")
    assert col_node("a") != col_node("b")
    assert len({slot_node("a", LOW), box_node("a", LOW), col_node("a"), pin_node("a", "L")}) == 4


def test_every_node_pack_row_emits_is_one_of_the_names() -> None:
    """A card with three attached columns: each solved node satisfies exactly one predicate."""
    syms = {"box": card("box", 3), "a": elem("a")}
    cols = tuple(column(f"c{i}", lane("a"), head=boxpin_end("box", f"p{i}")) for i in (1, 2, 3))
    block = card_block("box", tuple(c.id for c in cols), tuple((f"p{i}", "S") for i in (1, 2, 3)))
    attach = attachments(cols, {block.id: block})
    pcs = {c.id: PlacedColumn(c.id, (c.lanes[0].cells,), (0,), 0, flipped=False) for c in cols}
    options = core_options(
        justify=False,
        flip_turn="R180",
        tag_stagger=True,
        label_gap=8,
        parallel_pitch=48,
        driver_first=True,
        arrow_sides=("E", "W"),
    )
    spec = RowSpec(tuple(pcs), (block,), pcs, syms, frozenset(), options, attach)
    nodes = solve_row(spec, 1312)[0]
    assert nodes
    for node in (n for n in nodes if n != ORIGIN):  # the solver anchor is no pack_row name
        assert sum(p(node) for p in PREDICATES) == 1, node
    assert pin_node("box", "p1") in nodes
    assert box_node("box", LOW) in nodes
    assert slot_node(block.id, HIGH) in nodes
