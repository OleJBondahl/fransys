"""The row and page DP on hand-built problems: wraps, cards, forced breaks, fill, P2, widths.

A page holds 1280 x 822 G inside the 16 G margins. Sizes are in G; the designation label is
Size(16, 8) and a column symbol's reach is its footprint (hard, so no stagger) unless a test says.
"""

from __future__ import annotations

import re
from dataclasses import replace

from options_fixtures import core_options
from turn_fixtures import refit

from fransys_layout.core import Box, Hints, Sym
lazy from fransys_layout.core.values import CutResult

from .conftest import MARKER
from .cut_fixtures import box_sym, cut_of, elem, net, side
from .pack_fixtures import card


def rows_of(result: CutResult) -> list[list[tuple[str, ...]]]:
    return [[row.columns for row in p.rows] for p in result.spec.pages]


def test_wide_fan_wraps_to_a_second_row_of_the_same_page() -> None:
    """Thirteen 150 G columns total 1950 G, over the 1280 G row; the fan wraps, it does not page."""
    legs = [f"l{i:02d}" for i in range(12)]
    syms = [elem("src", 150), *(elem(leg, 150) for leg in legs)]
    result = cut_of(syms, [net("bus", "src.s", *(f"{leg}.n" for leg in legs))])
    (page,) = result.spec.pages
    assert len(page.rows) >= 2


def test_card_block_is_never_split_across_rows() -> None:
    """Four 320 G coils on a card are over the 1280 G row; cut by column they would split."""
    syms = [card("box", 4, north=2), *(elem(f"k{i}", 320) for i in range(1, 5))]
    result = cut_of(syms, [net(f"c{i}", f"box.p{i}", f"k{i}.n") for i in range(1, 5)])
    (block,) = (b for lst in result.blocks for b in lst.blocks)
    (page,) = result.spec.pages
    assert block.keep_whole
    assert [set(row.columns) for row in page.rows] == [{c.id for c in result.flow.columns}]


def test_break_before_group_starts_a_new_page() -> None:
    syms = [elem(f"{p}{i}", group=f"G{n}") for n, p in ((1, "a"), (2, "b")) for i in (1, 2)]
    nets = [net("x", "a1.s", "a2.n"), net("y", "b1.s", "b2.n")]
    order = Hints(group_order=("G1", "G2"))
    together = cut_of(syms, nets, hints=order)
    apart = cut_of(syms, nets, hints=replace(order, break_before=frozenset({"G2"})))
    assert len(together.spec.pages) == 1
    assert [(p.groups, len(p.rows[0].columns)) for p in apart.spec.pages] == [
        (("G1",), 1),
        (("G2",), 1),
    ]


def pair_case(c_height: int) -> list[Sym]:
    """Columns A B C D in this order; p joins B and C. A and B fill a row, C cannot join it."""
    return [
        elem("a0", 600, 180, "G1"),
        elem("a1", 600, 180, "G1"),
        side("b", 600, 400, "G2"),
        side("c", 600, c_height, "G2"),
        elem("d0", 200, 200, "G3"),
        elem("d1", 200, 200, "G3"),
    ]


PAIR_NETS = [net("ra", "a0.s", "a1.n"), net("p", "b.e", "c.e"), net("rd", "d0.s", "d1.n")]
PAIR_ORDER = Hints(group_order=("G1", "G2", "G3"))


def test_a_page_cut_through_a_two_pin_net_is_not_taken_when_a_row_cut_holds_it() -> None:
    """C is short, so a second row below A and B holds it: the pair stays on page 1."""
    result = cut_of(pair_case(200), PAIR_NETS, hints=PAIR_ORDER)
    assert rows_of(result) == [[("c:a0", "c:b"), ("c:c",)], [("c:d0",)]]


def test_the_same_page_cut_wins_when_the_pair_violation_costs_nothing() -> None:
    """Can fail: without the P2 weight the cut between B and C balances the two pages."""
    result = cut_of(
        pair_case(200),
        PAIR_NETS,
        hints=PAIR_ORDER,
        options=core_options(
            marker=MARKER,
            w_violation=0.0,
            flip_turn="R180",
            tag_stagger=True,
            label_gap=8,
            parallel_pitch=48,
            driver_first=True,
            arrow_sides=("E", "W"),
        ),
    )
    assert rows_of(result) == [[("c:a0", "c:b")], [("c:c", "c:d0")]]


def test_a_page_cut_through_a_two_pin_net_is_taken_when_no_row_cut_can_hold_it() -> None:
    """C is 400 G tall, so no second row can hold it: the page cut through the pair is left."""
    result = cut_of(pair_case(400), PAIR_NETS, hints=PAIR_ORDER)
    where = {c: p.page for p in result.spec.pages for r in p.rows for c in r.columns}
    assert (where["c:b"], where["c:c"]) == (1, 2)


def fill_syms() -> list[Sym]:
    """Column A is small; column B is too wide to share a row with A and too tall for a second."""
    return [
        elem("a0", 100, 50, "G1"),
        elem("a1", 100, 50, "G1"),
        elem("b0", 1200, 346, "G2"),
        elem("b1", 1200, 346, "G2"),
    ]


FILL_NETS = [net("ra", "a0.s", "a1.n"), net("rb", "b0.s", "b1.n")]


def test_a_page_under_the_minimum_fill_is_refused_unless_it_is_the_last() -> None:
    """A alone is page 1 at 1% fill and no other cut exists: kept and reported, never raised."""
    a_first = Hints(group_order=("G1", "G2"))
    thin = cut_of(fill_syms(), FILL_NETS, hints=a_first)
    assert [f.code for f in thin.spec.findings] == ["FILL_UNDER_MIN"]
    assert thin.spec.findings[0].page == 1
    text = thin.spec.findings[0].text
    assert re.fullmatch(
        r"unit \S*, block \S+: page filled 1% \(below min_fill 25%\): "
        r"the cut kept the block whole; lower min_fill or split the unit",
        text,
    ), text
    relaxed = cut_of(
        fill_syms(),
        FILL_NETS,
        hints=a_first,
        options=core_options(
            marker=MARKER,
            min_fill=0.0,
            flip_turn="R180",
            tag_stagger=True,
            label_gap=8,
            parallel_pitch=48,
            driver_first=True,
            arrow_sides=("E", "W"),
        ),
    )
    assert relaxed.spec.findings == ()  # can fail: only min_fill differs
    assert rows_of(relaxed) == [[("c:a0",)], [("c:b0",)]]
    a_last = cut_of(fill_syms(), FILL_NETS, hints=Hints(group_order=("G2", "G1")))
    assert rows_of(a_last) == [[("c:b0",)], [("c:a0",)]]
    assert a_last.spec.findings == ()


def test_a_row_that_stage_5_packs_wider_than_the_page_is_wrapped() -> None:
    """17 columns of 65 G wrap after 16: the pack modules put them further apart than their sum."""
    syms = [elem(f"{s}{i:02d}", 65) for i in range(17) for s in "ab"]
    nets = [net(f"n{i:02d}", f"a{i:02d}.s", f"b{i:02d}.n") for i in range(17)]
    (page,) = cut_of(syms, nets).spec.pages
    assert [len(row.columns) for row in page.rows] == [16, 1]


def card_row(left: int, right: int, width: int = 64) -> list[int]:
    """Box A1 with 16 columns of `width` G between free columns of `left` and `right` G."""
    syms = [box_sym(16), *(elem(f"k{i:02d}", width, 32, "CH") for i in range(1, 17))]
    for name, w, group in (("f", left, "FR"), ("g", right, "GR")):
        syms += [elem(f"{name}{n}", w, 32, group) for n in (0, 1)]
    nets = [net(f"n{i:02d}", f"A1.p{i}", f"k{i:02d}.n") for i in range(1, 17)]
    nets += [net("fr", "f0.s", "f1.n"), net("gr", "g0.s", "g1.n")]
    hints = Hints(group_order=("FR", "PLC", "CH", "GR"))
    (page,) = cut_of(syms, nets, hints=hints).spec.pages
    return [len(row.columns) for row in page.rows]


def test_free_columns_either_side_of_a_card_share_its_row_while_stage_5_packs_it_into_the_page() -> (  # noqa: E501 -- the order fixes this test name
    None
):
    """Free columns join the card's row exactly while the pack modules' width fits the page."""
    got = (card_row(56, 64), card_row(58, 64), card_row(16, 16, width=65))
    assert got == ([18], [17, 1], [1, 16, 1])


def test_neighbours_whose_texts_stagger_pack_at_the_narrow_pitch_but_the_row_counts_the_full_reach() -> (  # noqa: E501 -- the order fixes this test name
    None
):
    """Texts 100 G wide round a 56 G body stagger: soft meets soft, so the pitch is 88 G, not 112.

    14 columns span 13 * 88 + 100 = 1244, 15 span 1332 (the row counts the full text at its ends);
    with the stagger off the pitch is 112 and 11 columns span 10 * 112 + 100 = 1220.
    """
    syms = [
        refit(elem(f"{p}{i:02d}", 56), footprint=Box(-50, -16, 100, 32))
        for i in range(20)
        for p in "ab"
    ]
    nets = [net(f"n{i:02d}", f"a{i:02d}.s", f"b{i:02d}.n") for i in range(20)]
    staggered, plain = (
        cut_of(
            syms,
            nets,
            options=core_options(
                marker=MARKER,
                tag_stagger=on,
                label_gap=8,
                parallel_pitch=48,
                flip_turn="R180",
                driver_first=True,
                arrow_sides=("E", "W"),
            ),
        ).spec.pages
        for on in (True, False)
    )
    assert [len(row.columns) for row in staggered[0].rows] == [14, 6]
    assert [len(row.columns) for row in plain[0].rows] == [11, 9]


def test_a_single_block_wider_than_the_page_is_cut_as_a_row_of_its_own() -> None:
    """A column 1400 G wide is a row of its own; the cut returns and the next column wraps."""
    syms = [elem("w0", 1400, 32, "G1"), elem("w1", 1400, 32, "G1"), elem("s0", 100, 32, "G2")]
    syms.append(elem("s1", 100, 32, "G2"))
    nets = [net("a", "w0.s", "w1.n"), net("b", "s0.s", "s1.n")]
    result = cut_of(syms, nets, hints=Hints(group_order=("G1", "G2")))
    assert result.blocks[0].blocks[0].width_est > 1280
    assert rows_of(result)[0][0] == ("c:w0",)
    assert {c for r in rows_of(result) for row in r for c in row} == {"c:w0", "c:s0"}


def test_a_first_row_taller_than_the_page_gives_page_overflow_with_the_block_as_subject() -> None:
    """One 900 G symbol on an 822 G page: a page of its own and a finding naming its block."""
    result = cut_of([side("x", 100, 900), side("y", 100, 100)], [net("m", "x.e", "y.e")])
    (finding,) = result.spec.findings
    assert (finding.code, finding.page) == ("PAGE_OVERFLOW", 1)
    assert finding.subject == result.blocks[0].blocks[0].id


def test_a_row_after_the_first_holds_only_short_columns() -> None:
    """L7: y is 350 G tall (not short: 0.4 of the page is 329 G), so it cannot be the second row."""
    syms = [side("x", 700, 300), side("y", 700, 350)]
    nets = [net("m", "x.e", "y.e")]
    apart = cut_of(
        syms,
        nets,
        options=core_options(
            marker=MARKER,
            min_fill=0.0,
            flip_turn="R180",
            tag_stagger=True,
            label_gap=8,
            parallel_pitch=48,
            driver_first=True,
            arrow_sides=("E", "W"),
        ),
    )
    assert rows_of(apart) == [[("c:x",)], [("c:y",)]]
    short = cut_of(
        syms,
        nets,
        options=core_options(
            marker=MARKER,
            min_fill=0.0,
            short_height=0.5,
            flip_turn="R180",
            tag_stagger=True,
            label_gap=8,
            parallel_pitch=48,
            driver_first=True,
            arrow_sides=("E", "W"),
        ),
    )
    assert rows_of(short) == [[("c:x",), ("c:y",)]]  # y is short at 0.5: it takes a second row
