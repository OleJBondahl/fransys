"""A keep-whole fan wider alone than the page wraps at a column; other whole blocks stay whole.

Layout-0309: the wrap is the row-wrap arrow pair of stage 4; a card is never cut by column.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from options_fixtures import core_options

from fransys_layout.core.cut_costs import Boundary, Item
from fransys_layout.core.cut_dp import Cut, rows, splits_block
from fransys_layout.core.values import Block, CutResult, RefKind

from .conftest import MARKER
from .cut_fixtures import cut_of, elem, net

if TYPE_CHECKING:
    from fransys_layout.core.values import BlockKind


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
            flip_turn="R180",
            tag_stagger=True,
            label_gap=8,
            parallel_pitch=48,
            driver_first=True,
            arrow_sides=("E", "W"),
        ),
    )


def test_a_whole_block_that_is_not_a_fan_is_never_cut_by_column() -> None:
    cut = _cut_of_kind("card")
    assert splits_block(cut, 0, 1)
    assert splits_block(cut, 1, 2)


def test_a_wide_whole_fan_may_be_cut_by_column() -> None:
    cut = _cut_of_kind("fan")
    assert not splits_block(cut, 0, 1)
    assert rows(cut, 0)[2]  # a row of items 2..2 or 1..2 is a candidate: states exist
    # The row that ends at item 2 starts at item 2 only: the cut splits the fan before item 2.
    assert {st.start for st in rows(cut, 0)[2].values()} == {2}


def test_only_the_wide_fan_has_a_row_that_ends_inside_it() -> None:
    fan, card = rows(_cut_of_kind("fan"), 0), rows(_cut_of_kind("card"), 0)
    assert 0 in {st.start for sts in fan for st in sts.values()}
    assert any(st.start > 0 for sts in fan for st in sts.values())
    assert all(st.start == 0 for sts in card for st in sts.values())


def test_a_wide_fan_stays_whole_when_wrapping_is_off() -> None:
    cut = replace(
        _cut_of_kind("fan"),
        options=core_options(
            marker=MARKER,
            wrap_wide_fans=False,
            flip_turn="R180",
            tag_stagger=True,
            label_gap=8,
            parallel_pitch=48,
            driver_first=True,
            arrow_sides=("E", "W"),
        ),
    )
    assert splits_block(cut, 0, 1)
    assert all(st.start == 0 for sts in rows(cut, 0) for st in sts.values())


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
            flip_turn="R180",
            tag_stagger=True,
            label_gap=8,
            parallel_pitch=48,
            driver_first=True,
            arrow_sides=("E", "W"),
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
