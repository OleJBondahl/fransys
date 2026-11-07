"""Stage 2 authored hints: order_pairs (P1.4 E)."""

from __future__ import annotations

from fransys_layout.core.values import Hints

from .blocks_fixtures import build, flat, ids, loose


def test_order_pairs_moves_a_block_right_after_the_one_it_follows() -> None:
    syms, cols = loose("A", "B", "C")
    order = ("A", "B", "C")
    pairs = (("C", "A"),)
    assert ids(build(syms, cols, hints=Hints(group_order=order, order_pairs=pairs))) == [
        "c2",
        "c3",
        "c1",
    ]
    by_symbol = Hints(group_order=order, order_pairs=(("s3", "s1"),))
    assert ids(build(syms, cols, hints=by_symbol)) == ["c2", "c3", "c1"]
    unknown = Hints(group_order=order, order_pairs=(("A", "C"), ("A", "zz")))
    assert ids(build(syms, cols, hints=unknown)) == ["c1", "c2", "c3"]


def test_a_hint_name_is_never_a_block_id() -> None:
    syms, cols = loose("A", "B", "C")
    block_id = flat(build(syms, cols))[0].id
    hints = Hints(group_order=("A", "B", "C"), order_pairs=((flat(build(syms, cols))[2].id, block_id),))
    assert ids(build(syms, cols, hints=hints)) == ["c1", "c2", "c3"]


def test_order_pairs_cycle_ends_with_a_finding() -> None:
    syms, cols = loose("A", "B", "C")
    hints = Hints(group_order=("A", "B", "C"), order_pairs=(("A", "B"), ("B", "A")))
    assert [f.code for f in build(syms, cols, hints=hints)[0].findings] == ["ORDER_HINT_UNMET"]
