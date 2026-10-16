"""Stage 5, y: the alignments of a page as values, before any is solved."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from fransys_layout.core import Facts, Options, PinRef
from fransys_layout.core.geometry import pin_xy
from fransys_layout.core.pack import cell_node
from fransys_layout.core.place_align import (
    Align,
    band_aligns,
    mate_aligns,
    page_aligns,
    row_group_aligns,
    unmet_mates,
)

from . import align_fixtures as fx
from .conftest import MARKER_BOX
from .place_fixtures import row_group_three
from .test_place_x import env_of

if TYPE_CHECKING:
    from fransys_layout.core.place_env import PageEnv


def _offset(env: PageEnv, sym: str, pin: str) -> int:
    """The y offset of a pin from its cell origin, at the cell's orientation."""
    cell = next(c for pc in env.pcs.values() for ln in pc.lanes for c in ln if c.sym == sym)
    return pin_xy(env.syms[sym], cell, pin)[1]


def _nodes(align: Align) -> list[str]:
    return [n for n, _ in align.lines[0]]


def test_band_ranks_align_across_columns() -> None:
    """Rank 1 joins a1 and b1, rank 2 joins a2 and b2, ascending rank; every builder builds."""
    for build in (fx.lane_two_of_a_rank, fx.mate_across_rows, fx.band_squeezes_driver):
        assert env_of(build()).pcs
    env = env_of(fx.two_band_columns())
    one, two = band_aligns(env)
    assert (one.kind, one.subject, two.subject) == ("band", "rank 1, row 0", "rank 2, row 0")
    assert _nodes(one) == [cell_node("c:a0", 0, 1), cell_node("c:b1", 0, 0)]
    assert _nodes(two) == [cell_node("c:a0", 0, 2), cell_node("c:b1", 0, 2)]
    assert all(s == 0 for _, s in one.lines[0])


def test_band_align_off_gives_no_band() -> None:
    env = env_of(fx.two_band_columns(), Options(marker=MARKER_BOX, band_align=False))
    assert band_aligns(env) == ()
    assert page_aligns(env) == ()


def test_a_lane_aligns_only_its_topmost_cell_of_a_rank() -> None:
    """A1 holds two cells of rank 1; only the upper one joins b1."""
    env = env_of(fx.lane_two_of_a_rank())
    (band,) = band_aligns(env)
    assert _nodes(band) == [cell_node("c:a1", 0, 0), cell_node("c:b1", 0, 0)]


def test_bands_of_different_rows_are_separate_aligns() -> None:
    """Rank 1 on row 0 has two members; the lone cell of row 1 makes no align."""
    env = env_of(fx.two_rows_equal_ranks())
    assert {pc.row for pc in env.pcs.values()} == {0, 1}
    (band,) = band_aligns(env)
    assert band.subject == "rank 1, row 0"
    assert len(band.lines[0]) == 2


def test_mated_pins_share_one_y() -> None:
    """The shift of each half is its pin's offset at its cell: p (48 tall) has s 24 below."""
    env = env_of(fx.mate_columns())
    (mate,) = mate_aligns(env)
    assert mate.kind == "mate"
    assert mate.subject == "p.s/q.n"
    assert [s for _, s in mate.lines[0]] == [_offset(env, "p", "s"), _offset(env, "q", "n")]
    assert mate.lines[0][0][1] == 24
    assert unmet_mates(env) == ()


def _turned(env: PageEnv, sym: str) -> PageEnv:
    """The env with every cell of `sym` turned R180."""
    pcs = {
        k: replace(
            pc,
            lanes=tuple(
                tuple(replace(c, orient="R180") if c.sym == sym else c for c in lane)
                for lane in pc.lanes
            ),
        )
        for k, pc in env.pcs.items()
    }
    return replace(env, pcs=pcs)


def test_mated_pins_respect_the_cells_orientation() -> None:
    """Turned R180, p.s lies 24 above its origin: the shift is the pin_xy of the turned cell."""
    env = _turned(env_of(fx.mate_columns()), "p")
    (mate,) = mate_aligns(env)
    assert _offset(env, "p", "s") == -24
    assert [s for _, s in mate.lines[0]] == [-24, _offset(env, "q", "n")]


def test_mates_off_the_page_are_left_alone_and_across_rows_are_returned() -> None:
    env = env_of(fx.mate_across_rows())
    assert mate_aligns(env) == ()
    assert unmet_mates(env) == ((PinRef("p", "s"), PinRef("r", "n")),)
    boxed = env_of(fx.mate_with_box())
    assert mate_aligns(boxed) == ()
    assert len(unmet_mates(boxed)) == 1
    prob = fx.mate_columns()
    gone = replace(prob, facts=Facts(mates=((PinRef("p", "s"), PinRef("elsewhere", "n")),)))
    env = env_of(gone)
    assert mate_aligns(env) == ()
    assert unmet_mates(env) == ()


def test_the_keep_order_is_mate_then_row_group_then_band() -> None:
    env = env_of(fx.all_three_contradict())
    assert [a.kind for a in page_aligns(env)] == ["mate", "row_group", "band"]


def test_row_groups_keep_their_head_and_foot_lines() -> None:
    env = env_of(row_group_three("G"))
    (group,) = row_group_aligns(env)
    assert group.kind == "row_group"
    assert group.subject == "G"
    assert env_of(row_group_three(None)).pcs
    assert row_group_aligns(env_of(row_group_three(None))) == ()
    assert len(group.lines) >= 1


def test_aligns_are_in_natural_order_whatever_the_input_order() -> None:
    """Mates given reversed, and each pair swapped, give the same Align values up to line order."""
    prob = fx.mate_columns()
    swapped = replace(prob, facts=Facts(mates=((PinRef("q", "n"), PinRef("p", "s")),)))
    first = mate_aligns(env_of(prob))[0]
    other = mate_aligns(env_of(swapped))[0]
    assert sorted(first.lines[0]) == sorted(other.lines[0])
    bands = band_aligns(env_of(fx.two_band_columns()))
    assert [b.subject for b in bands] == sorted(b.subject for b in bands)
