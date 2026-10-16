"""Stage 2 authored hints: order_pairs, chains, keep_together, break_before (P1.4 E)."""

from __future__ import annotations

from fransys_layout.core.values import Hints

from .blocks_fixtures import box_case, build, fan, flat, ids, loose


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
    hints = Hints(
        group_order=("A", "B", "C"), order_pairs=((flat(build(syms, cols))[2].id, block_id),)
    )
    assert ids(build(syms, cols, hints=hints)) == ["c1", "c2", "c3"]


def test_order_pairs_cycle_ends_with_a_finding() -> None:
    syms, cols = loose("A", "B", "C")
    hints = Hints(group_order=("A", "B", "C"), order_pairs=(("A", "B"), ("B", "A")))
    assert [f.code for f in build(syms, cols, hints=hints)[0].findings] == ["ORDER_HINT_UNMET"]


def test_chain_fixes_the_column_order_inside_its_block() -> None:
    syms, cols = loose("A", "A", "A", "B")
    fans = [fan("f1", "c1", "c2", "c3")]
    plain = next(b for b in flat(build(syms, cols, fans)) if b.kind == "fan")
    assert plain.columns == ("c1", "c2", "c3")
    assert not plain.fixed_order
    blocks = flat(build(syms, cols, fans, Hints(chains=(("s3", "s1"),))))
    swapped = next(b for b in blocks if b.kind == "fan")
    assert swapped.columns == ("c3", "c2", "c1")  # the chain's columns swap slots; c2 stays between
    assert swapped.fixed_order
    assert not next(b for b in blocks if b.kind == "column").fixed_order
    one = flat(build(syms, cols, fans, Hints(chains=(("s2",),))))  # one column fixes nothing
    assert not next(b for b in one if b.kind == "fan").fixed_order


def test_chain_leaves_a_card_in_pin_order() -> None:
    syms, cols = box_case(4, 64)
    card = flat(build(syms, cols, hints=Hints(chains=(("k3", "k1"),))))[0]
    assert card.columns == ("c1", "c2", "c3", "c4")
    assert not card.fixed_order


def test_keep_together_makes_blocks_consecutive_when_they_fit_one_page_width() -> None:
    syms, cols = loose("A", "C", "B", reach=(150, 150))
    hints = Hints(group_order=("A", "C", "B"), keep_together=(frozenset({"A", "B"}),))
    lists = build(syms, cols, hints=hints)
    assert ids(lists) == ["c1", "c3", "c2"]
    assert lists[0].findings == ()


def test_keep_together_unmet_gives_the_finding_and_leaves_the_order() -> None:
    syms, cols = loose("A", "C", "B", reach=(350, 350))  # 2 * (700 + 8) is over the 1280 page
    hints = Hints(group_order=("A", "C", "B"), keep_together=(frozenset({"A", "B"}),))
    lists = build(syms, cols, hints=hints)
    assert ids(lists) == ["c1", "c2", "c3"]
    assert [(f.code, f.subject) for f in lists[0].findings] == [("KEEP_TOGETHER_UNMET", "A,B")]


def test_break_before_marks_the_first_block_of_the_group() -> None:
    syms, cols = loose("A", "A", "B")
    order = ("A", "B")
    first = flat(build(syms, cols, hints=Hints(group_order=order, break_before=frozenset({"A"}))))
    assert [b.forced_break_before for b in first] == [True, False, False]
    last = flat(build(syms, cols, hints=Hints(group_order=order, break_before=frozenset({"B"}))))
    assert [b.forced_break_before for b in last] == [False, False, True]
