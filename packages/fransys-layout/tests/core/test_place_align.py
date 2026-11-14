"""Stage 5, y: the alignments of a page as values, before any is solved."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import pytest
from turn_fixtures import refit

from fransys_layout.core import Box, Facts, PinRef, Placed, PlacementProblem
from fransys_layout.core.errors import CoreError
from fransys_layout.core.geometry import pin_xy
from fransys_layout.core.pack import cell_node
from fransys_layout.core.place_align import (
    Align,
    _beside,
    band_aligns,
    mate_aligns,
    page_aligns,
    row_group_aligns,
    unmet_mates,
)
from fransys_layout.core.place_assemble import assemble
from fransys_layout.core.place_x import place_x
from fransys_layout.core.place_y import place_y

from . import align_fixtures as fx
from .cut_fixtures import AREA, chain, elem
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
            lanes=tuple(tuple(replace(c, orient="R180") if c.sym == sym else c for c in lane) for lane in pc.lanes),
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
    gone = replace(
        prob,
        facts=Facts(mates=((PinRef("p", "s"), PinRef("elsewhere", "n")),), far_ends=()),
    )
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
    assert group.subject == "G, row 0"
    assert env_of(row_group_three(None)).pcs
    assert row_group_aligns(env_of(row_group_three(None))) == ()


def test_aligns_are_in_natural_order_whatever_the_input_order() -> None:
    """Mates given reversed, and each pair swapped, give the same Align values up to line order."""
    prob = fx.mate_columns()
    swapped = replace(prob, facts=Facts(mates=((PinRef("q", "n"), PinRef("p", "s")),), far_ends=()))
    first = mate_aligns(env_of(prob))[0]
    other = mate_aligns(env_of(swapped))[0]
    assert sorted(first.lines[0]) == sorted(other.lines[0])
    bands = band_aligns(env_of(fx.two_band_columns()))
    assert [b.subject for b in bands] == sorted(b.subject for b in bands)


def _runs(prob: PlacementProblem, dropped: frozenset[str] = frozenset()) -> list[tuple[set[str], str]]:
    """The strip runs the page is assembled with: (members as a set, key); each run's members stand left to right."""
    env = env_of(prob)
    x, _ = place_x(env)
    page = assemble(env, x, place_y(env, x)[0], dropped)
    at = {p.sym: p.body.x for p in page.placed}
    assert all([at[m] for m in r.members] == sorted(at[m] for m in r.members) for r in page.runs)
    return [(set(r.members), r.key) for r in page.runs]


def test_strip_terminals_level_in_a_row_a_gap_apart_are_one_run_each() -> None:
    """STRIP-TAG-ONCE: three hubs of a row group at the heads stand a gap apart, so each is its own run, with its Align kept or lost."""
    kept = _runs(row_group_three("G"))
    assert [m for m, _ in kept] == [{"h0"}, {"h1"}, {"h2"}]
    assert all(key.startswith("G run at h") for _, key in kept)
    assert [m for m, _ in _runs(row_group_three("G"), frozenset({"G, row 0"}))] == [{"h0"}, {"h1"}, {"h2"}]
    assert _runs(row_group_three(None)) == []


def _at(sym: str, x: int) -> Placed:
    return Placed(sym, 1, x, 0, "R0", Box(x, 0, 16, 16), Box(x, 0, 16, 16), ())


def test_neighbours_within_one_pitch_stay_one_run_and_a_wider_gap_cuts_it() -> None:
    """STRIP-TAG-ONCE, R2096: a gap of nothing or of one pitch (the footprint width) keeps one run, left to right; a wider gap starts another."""
    placed = {s: _at(s, x) for s, x in (("a", 0), ("b", 16), ("c", 48), ("d", 64), ("e", 97))}
    assert _beside(["a", "b", "c", "d"], placed) == [["a", "b", "c", "d"]]
    assert _beside(["a", "b", "c", "d", "e"], placed) == [["a", "b", "c", "d"], ["e"]]
    assert _beside(["a", "b"], {"a": placed["a"], "b": _at("b", 33)}) == [["a"], ["b"]]


def test_a_strip_terminal_at_neither_end_of_its_column_is_a_run_of_one() -> None:
    """The middle of a column is no head and no foot: not level with any other, it stands alone."""
    mid = refit(elem("m"), row_group="G")
    prob = PlacementProblem(AREA, (elem("a"), mid, elem("b")), tuple(chain(["a", "m", "b"])), facts=Facts(far_ends=()))
    assert _runs(prob) == [({"m"}, "G run at m")]


def test_a_run_key_that_is_a_symbol_id_is_refused_naming_the_strip() -> None:
    """The key is the run's annex owner: one id space with the symbols."""
    syms = (elem("a"), refit(elem("m"), row_group="G"), elem("b"), elem("G run at m"))
    prob = PlacementProblem(AREA, syms, tuple(chain(["a", "m", "b", "G run at m"])), facts=Facts(far_ends=()))
    with pytest.raises(CoreError, match="strip G"):
        _runs(prob)
