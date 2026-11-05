"""A keep-whole fan wider alone than the page wraps at a column; other whole blocks stay whole.

Layout-0309: the wrap is the row-wrap arrow pair of stage 4; a card is never cut by column.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from options_fixtures import core_options

from fransys_layout.core.arrow_reserve import RowReserve
from fransys_layout.core.cut_costs import Boundary, Item
from fransys_layout.core.cut_dp import Cut, row_size, row_sizes, rows, splits_block, wraps
from fransys_layout.core.cut_measured import with_legs
from fransys_layout.core.flow_values import Block, BlockList, CutResult
from fransys_layout.core.values import RefKind

from .conftest import MARKER
from .cut_fixtures import cut_of, elem, net

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.core.flow_values import BlockKind


def wide_fan_cut(legs: int = 8, width: int = 100) -> CutResult:
    """A bus feeding `legs` columns, each two parallel members (a multi-lane column, keep-whole)."""
    syms = [elem("src", 150)]
    buses = [f"{p}{i:02d}.n" for p in "ab" for i in range(legs)]
    nets = [net("bus", "src.s", *buses)]
    for i in range(legs):
        syms += [elem(f"a{i:02d}", width), elem(f"b{i:02d}", width)]
        nets.append(net(f"y{i:02d}", f"a{i:02d}.s", f"b{i:02d}.s"))
    return cut_of(syms, nets)


def test_a_keep_whole_fan_wider_than_the_room_wraps_with_one_arrow_pair() -> None:
    result = wide_fan_cut()
    (block,) = (b for lst in result.blocks for b in lst.blocks)
    assert (block.kind, block.keep_whole) == ("fan", True)
    assert block.width_est > 1280
    (page,) = result.spec.pages
    assert len(page.rows) == 2
    arrows = [r for r in result.spec.reference_plan if r.kind == RefKind.ARROW]
    assert len(arrows) == 1


def _cut_of_kind(kind: BlockKind) -> Cut:
    """Three whole items of one block 600 G apart on a 1280 G page: 1800 G alone."""
    block = Block(
        id="b",
        kind=kind,
        unit="",
        columns=("c0", "c1", "c2"),
        anchor=None,
        fan="f" if kind == "fan" else None,
        group=None,
        width_est=1800,
        height_est=40,
        short=True,
        keep_whole=True,
        forced_break_before=False,
        seat="none",
    )
    seq = [
        Item(
            block="b",
            column=f"c{i}",
            height=40,
            short=True,
            whole=True,
            forced_break_before=False,
            at=600 * i + 60,
            lead=60,
            tail=60,
            seat="none",
        )
        for i in range(3)
    ]
    return Cut(
        seq,
        [Boundary(1, 0, 0, ("f",), ())] * 2,
        {"b": block},
        1280,
        800,
        core_options(
            marker=MARKER,
        ),
    )


def test_a_whole_block_that_is_not_a_fan_is_never_cut_by_column() -> None:
    cut = _cut_of_kind("card")
    assert splits_block(cut, 0, 1)
    assert splits_block(cut, 1, 2)


def test_a_wide_whole_fan_may_be_cut_by_column() -> None:
    cut = _cut_of_kind("fan")
    assert not splits_block(cut, 0, 1)
    assert rows(cut, 0, row_sizes(cut))[2]  # a row of items 2..2 or 1..2 is a candidate: states exist
    # The row that ends at item 2 starts at item 2 only: the cut splits the fan before item 2.
    assert {st.start for st in rows(cut, 0, row_sizes(cut))[2].values()} == {2}


def test_only_the_wide_fan_has_a_row_that_ends_inside_it() -> None:
    kinds = (_cut_of_kind("fan"), _cut_of_kind("card"))
    fan, card = (rows(c, 0, row_sizes(c)) for c in kinds)
    assert 0 in {st.start for sts in fan for st in sts.values()}
    assert any(st.start > 0 for sts in fan for st in sts.values())
    assert all(st.start == 0 for sts in card for st in sts.values())


def test_a_wide_fan_stays_whole_when_wrapping_is_off() -> None:
    cut = replace(
        _cut_of_kind("fan"),
        options=core_options(
            marker=MARKER,
            wrap_wide_fans=False,
        ),
    )
    assert splits_block(cut, 0, 1)
    assert all(st.start == 0 for sts in rows(cut, 0, row_sizes(cut)) for st in sts.values())


def test_without_wrapping_the_fan_page_has_one_row() -> None:
    syms = [elem("src", 150)] + [elem(f"{p}{i:02d}", 100) for i in range(8) for p in "ab"]
    nets = [net("bus", "src.s", *[f"{p}{i:02d}.n" for p in "ab" for i in range(8)])]
    nets += [net(f"y{i:02d}", f"a{i:02d}.s", f"b{i:02d}.s") for i in range(8)]
    result = cut_of(
        syms,
        nets,
        options=core_options(
            marker=MARKER,
            wrap_wide_fans=False,
        ),
    )
    (page,) = result.spec.pages
    assert len(page.rows) == 1


def test_a_wrapped_wide_fan_in_two_rows_is_not_a_block_not_placed() -> None:
    """The stage 4 guard takes the wrap (layout-0309): rows > 1 for a wide fan is no finding."""
    result = wide_fan_cut()
    (page,) = result.spec.pages
    assert len(page.rows) == 2
    assert "BLOCK_NOT_PLACED" not in {f.code for f in result.spec.findings}


def _two_cards(arrows: Mapping[str | tuple[str, str], RowReserve]) -> Cut:
    """Two one-item card blocks whose row is 1190 G of footprints on a 1280 G page; `arrows` is what the round before measured."""
    base = _cut_of_kind("card")
    card = replace(base.by_id["b"], width_est=100, keep_whole=False)
    blocks = {"b0": replace(card, id="b0", anchor="A"), "b1": replace(card, id="b1", anchor="B")}
    seq = [replace(base.seq[0], block="b0", at=60), replace(base.seq[1], block="b1", at=1130)]
    return Cut(seq, [Boundary(0, 0, 0, (), ())], blocks, 1280, 800, base.options, arrows)


def test_a_rows_card_tap_arrows_count_in_its_width_and_the_row_is_cut() -> None:
    free, tapped = _two_cards({}), _two_cards({"A": RowReserve(166)})
    assert (row_size(free, 0, 1)[0], row_size(tapped, 0, 1)[0]) == (1190, 1190 + 166)
    assert {st.start for st in rows(free, 0, row_sizes(free))[1].values()} == {0, 1}
    assert {st.start for st in rows(tapped, 0, row_sizes(tapped))[1].values()} == {1}


def _legged() -> dict[str | tuple[str, str], RowReserve]:
    """Two fans' legs: the fan `f` 100 G at c0 and 50 G at c1; the fan `g` 90 G at c2 (R1618)."""
    return {
        ("b", "c0"): RowReserve(legs=(("f", 100),), tail=8),
        ("b", "c1"): RowReserve(legs=(("f", 50),), tail=4),
        ("b", "c2"): RowReserve(legs=(("g", 90),), tail=8),
    }


def test_a_row_takes_the_legs_of_its_columns_added_for_one_fan_and_the_widest_fan_wins() -> None:
    cut = replace(_cut_of_kind("fan"), arrows=_legged())
    bare = row_size(_cut_of_kind("fan"), 0, 2)[0]
    assert row_size(cut, 0, 2)[0] - bare == 150 + 8  # fan f: 100 + 50 and the widest tail
    assert row_size(cut, 2, 2)[0] - row_size(_cut_of_kind("fan"), 2, 2)[0] == 98


def test_a_fan_that_fits_alone_wraps_once_its_legs_are_counted() -> None:
    block = replace(_cut_of_kind("fan").by_id["b"], width_est=1100)
    options = _cut_of_kind("fan").options
    assert not wraps(block, 1280, options)
    (listed,) = with_legs((BlockList("", (block,)),), _legged())
    assert wraps(listed.blocks[0], 1280, options)


def test_a_wrapped_fan_column_row_is_as_tall_as_the_stub_boxes_at_its_trunk_end() -> None:
    """R1634: a column item that is not whole takes `RowReserve.y` of its (block, column) entry into the row's height."""
    base = _cut_of_kind("fan")
    cut = replace(base, seq=[replace(it, whole=False) for it in base.seq])
    stubbed = replace(cut, arrows={("b", "c1"): RowReserve(y=456)})
    assert row_size(stubbed, 1, 1)[1] - row_size(cut, 1, 1)[1] == 456
    assert row_size(stubbed, 0, 0)[1] == row_size(cut, 0, 0)[1]
