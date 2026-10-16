"""Stage 2 on hand-built flows: members, groups, cards, fans and the estimates (P1.4 D)."""

from __future__ import annotations

from dataclasses import replace

from fransys_layout.core.blocks_members import column_group
from fransys_layout.core.pack_row import row_width
from fransys_layout.core.rowspec import one_row
from fransys_layout.core.values import BlockList, Cell, CycleSplit, FlowGraph, Hints, Lane, Options

from .blocks_fixtures import (
    AREA,
    box_case,
    box_sym,
    build,
    by_anchor,
    column,
    fan,
    flat,
    ids,
    loose,
    problem_of,
    sym,
)


def test_column_group_majority_with_the_tie_to_the_foot() -> None:
    syms = {s.id: s for s in (sym("a", "G1"), sym("b", "G2"), sym("n", None))}
    assert column_group(column("c1", "a", "b"), syms) == "G2"  # one vote each: the foot's group
    assert column_group(column("c2", "b", "a"), syms) == "G1"
    assert column_group(column("c3", "a", "a", "b"), syms) == "G1"  # a majority beats the foot
    assert column_group(column("c4", "n", "n", "a"), syms) == "G1"  # None votes not
    assert column_group(column("c5", "n"), syms) is None
    block = flat(build([sym("a", "G1"), sym("b", "G2")], [column("c1", "a", "b")]))[0]
    assert block.group == "G2"


def test_attached_column_takes_its_card_whatever_its_group() -> None:
    syms = [box_sym("A1", "PLC", 2), sym("k1", "R1"), sym("k2", "R2")]
    cols = [column("c1", "k1", pin=("A1", "p1")), column("c2", "k2")]
    hints = Hints(group_order=("PLC", "R1", "R2"))
    lists = build(syms, cols, [fan("f1", "c1", "c2")], hints)
    blocks = flat(lists)
    assert [(b.kind, b.columns) for b in blocks] == [("card", ("c1",)), ("fan", ("c2",))]
    assert (blocks[0].group, blocks[0].anchor) == ("PLC", "A1")
    assert blocks[1].fan == "f1"  # the fan keeps only its free columns


def test_fan_takes_the_majority_group_of_its_legs() -> None:
    syms = [sym("s1", "B"), sym("s2", "A"), sym("s3", "A")]
    cols = [column("c1", "s1"), column("c2", "s2"), column("c3", "s3")]
    assert flat(build(syms, cols, [fan("f1", "c1", "c2", "c3")]))[0].group == "A"


def test_fan_tie_goes_to_the_lowest_group_in_group_order_then_natural() -> None:
    syms = [sym("s1", "R11"), sym("s2", "R5")]
    cols = [column("c1", "s1"), column("c2", "s2")]
    fans = [fan("f1", "c1", "c2")]
    assert flat(build(syms, cols, fans, Hints(group_order=("R11", "R5"))))[0].group == "R11"
    assert flat(build(syms, cols, fans, Hints(group_order=("R5", "R11"))))[0].group == "R5"
    assert flat(build(syms, cols, fans))[0].group == "R5"  # no order: natural, R5 before R11


def test_blocks_come_in_group_order_then_natural_key() -> None:
    syms, cols = loose("B", "A", "B")
    assert ids(build(syms, cols, hints=Hints(group_order=("A", "B")))) == ["c2", "c1", "c3"]
    syms, cols = loose("A", "A", "A", "A", "A", "A", "A", "A", "A", "A")
    assert ids(build(syms, cols)) == [f"c{i}" for i in range(1, 11)]  # c2 before c10


def test_each_unit_gets_its_own_list_and_the_empty_flow_one_empty_list() -> None:
    syms = [sym("s1", "A", "u2"), sym("s2", "A", "u1")]
    lists = build(syms, [column("c1", "s1"), column("c2", "s2")])
    assert [(bl.unit, [b.columns for b in bl.blocks]) for bl in lists] == [
        ("u1", [("c2",)]),
        ("u2", [("c1",)]),
    ]
    assert build([], []) == (BlockList("", ()),)


def test_a_card_keeps_its_columns_in_pin_order_and_its_edges() -> None:
    syms, cols = box_case(16, 94)
    lists = build(syms, cols)
    card = flat(lists)[0]
    assert card.columns == tuple(f"c{i}" for i in range(1, 17))
    assert dict(card.pin_edges) == {f"p{i}": "N" if i <= 8 else "S" for i in range(1, 17)}
    assert card.width_est == 822
    assert lists[0].findings == ()


def test_card_overfull_spilled_columns_become_free_blocks_with_a_finding() -> None:
    syms, cols = box_case(40, 64)
    lists = build(syms, cols)
    blocks = by_anchor(lists)
    spilled = {"c18", "c19", "c20", "c38", "c39", "c40"}
    assert set(blocks["A1"].columns) == {f"c{i}" for i in range(1, 41)} - spilled
    assert blocks["A1"].width_est == 1248
    assert len(blocks) == 1 + len(spilled)
    for c in spilled:
        free = blocks[c]
        assert (free.kind, free.columns, free.anchor, free.group) == ("column", (c,), None, "CH")
    assert [(f.code, f.subject) for f in lists[0].findings] == [("CARD_OVERFULL", "A1")]


def test_width_est_is_the_row_width_of_the_blocks_own_row() -> None:
    syms, cols = loose("A", "A", "A")
    lists = build(syms, cols, [fan("f1", "c1", "c2", "c3")])
    block = flat(lists)[0]
    flow_cols = tuple(cols)

    flow = FlowGraph(flow_cols, (), (), (), CycleSplit(0, 0, 0), ())
    row = one_row(block.columns, (block,), flow, problem_of(syms), Options())
    assert block.width_est == row_width(row) > 0


def test_estimates_short_and_keep_whole() -> None:
    syms, cols = box_case(4, 64)
    card = flat(build(syms, cols))[0]
    assert card.height_est == 32 + 32 + 8  # box body, the tallest column on the one edge, a wire
    assert card.short is (card.height_est < Options().short_height * AREA.h)
    assert card.keep_whole
    syms, cols = loose("A", "A")
    fanned = flat(build(syms, cols, [fan("f1", "c1", "c2")]))[0]
    assert (fanned.height_est, fanned.keep_whole) == (32 + 2 * 8 * 1, False)
    two = replace(cols[0], lanes=(cols[0].lanes[0], Lane((Cell("s2", "R0", None, None),), 40)))
    assert flat(build(syms, [two, cols[1]]))[0].keep_whole  # a multi-lane column is kept whole
    assert not flat(build(syms, cols))[0].keep_whole
