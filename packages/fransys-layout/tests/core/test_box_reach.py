"""Stage 4 row width against the placed extent when a card box footprint reaches past its body."""

from __future__ import annotations

import pytest
from options_fixtures import core_options
from turn_fixtures import refit

from fransys_layout.core import Box, PlacementProblem
from fransys_layout.core.geometry import box_reach
from fransys_layout.core.node_names import HIGH, box_node, col_node
from fransys_layout.core.pack_row import row_width, solve_row
from fransys_layout.core.place_env import page_envs
from fransys_layout.core.place_x import row_specs
from fransys_layout.core.rowspec import one_row

from .pack_fixtures import boxpin_end, card, card_block, column, elem, free_block, lane
from .pipeline_fixtures import cut_of, placed_of
from .place_fixtures import card_with_label, footprints
from .test_rowspec import world


def _extent(prob: PlacementProblem) -> tuple[int, int]:
    """(placed extent, row_width) of the first row of the first page, justify off."""
    options = core_options(
        justify=False,
        flip_turn="R180",
        tag_stagger=True,
        label_gap=8,
        parallel_pitch=48,
        driver_first=True,
        arrow_sides=("E", "W"),
    )
    cut = cut_of(prob, options)
    env = page_envs(cut, prob, options)[0]
    spec = row_specs(env)[0]
    fps = footprints(placed_of(prob, options).pages[0])
    left = min(f.x for f in fps.values())
    return max(f.x + f.w for f in fps.values()) - left, row_width(spec)


@pytest.mark.parametrize("grow", [0, 16, 52])
def test_row_width_includes_the_card_footprint(grow: int) -> None:
    placed, measured = _extent(card_with_label(grow))
    assert placed == measured


def test_a_row_without_a_card_is_unchanged() -> None:
    placed, measured = _extent(card_with_label(0))
    assert placed == measured


def test_a_card_whose_footprint_is_its_body_reaches_nothing() -> None:
    assert box_reach(card("box", 3)) == (0, 0)


def test_the_reach_is_the_footprint_minus_the_body() -> None:
    sym = card("box", 3)
    wide = refit(sym, footprint=Box(-4, 0, sym.body.w + 4 + 52, 32))
    assert box_reach(wide) == (4, 52)


def test_a_symbol_without_a_box_spec_has_no_reach() -> None:
    with pytest.raises(ValueError, match="no box spec"):
        box_reach(elem("a"))


def test_a_footprint_inside_the_body_is_refused() -> None:
    sym = card("box", 3)
    with pytest.raises(ValueError, match="holds its body"):
        box_reach(refit(sym, footprint=Box(0, 0, 8, 32)))


def test_a_card_in_the_middle_keeps_the_next_column_clear_by_its_footprint() -> None:
    sym = card("box", 3)
    wide = refit(sym, footprint=Box(0, 0, sym.body.w + 300, 32))
    syms = [wide, elem("a", body=Box(-2, -16, 4, 32))]
    cols = [column(f"c{i}", lane("a"), head=boxpin_end("box", f"p{i}")) for i in (1, 2, 3)]
    cols.append(column("c4", lane("a")))
    names = tuple(c.id for c in cols)
    block = card_block("box", names[:3], tuple((f"p{i}", "S") for i in (1, 2, 3)))
    flow, prob = world(syms, cols)
    spec = one_row(
        names,
        (block, free_block("f", ("c4",))),
        flow,
        prob,
        core_options(
            justify=False,
            flip_turn="R180",
            tag_stagger=True,
            label_gap=8,
            parallel_pitch=48,
            driver_first=True,
            arrow_sides=("E", "W"),
        ),
    )
    x, _ = solve_row(spec, 10_000)
    assert x[col_node("c4")] - 2 >= x[box_node("box", HIGH)] + 300
