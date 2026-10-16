"""Stage 5 end to end: pins on the grid, no overlaps, widths agree, respelling changes nothing."""

from __future__ import annotations

from dataclasses import replace
from itertools import combinations
from typing import TYPE_CHECKING

import pytest

from fransys_layout.core import Options, PlacementProblem
from fransys_layout.core.geometry import overlaps
from fransys_layout.core.pack_row import row_width
from fransys_layout.core.place_env import page_envs
from fransys_layout.core.place_x import row_specs

from .conftest import MARKER_BOX
from .cut_respell import id_sets, make_maps, respell_problem
from .pipeline_fixtures import blocks_of, cut_of, flow_of, placed_of
from .place_fixtures import (
    all_pins,
    bundle_fan,
    card_with_coils,
    footprints,
    row_group_three,
    two_edge_card,
)
from .test_hub_cells import hub_shape

if TYPE_CHECKING:
    from fransys_layout.core import Placement

# Coil widths are multiples of 16 so a coil's half width, hence its pin x, is on the grid.
PLANTED = {
    "card_with_coils": lambda: card_with_coils(4, 80),
    "two_edge_card": lambda: two_edge_card(16, 96),
    "row_group_three": lambda: row_group_three("X1"),
    "bundle_fan": bundle_fan,
}


@pytest.mark.parametrize("name", PLANTED)
def test_every_pin_of_every_placed_symbol_lies_on_the_wiring_grid(name: str) -> None:
    step = Options(marker=MARKER_BOX).wiring_grid
    for (sym, pin), (x, y) in all_pins(placed_of(PLANTED[name]())).items():
        assert x % step == 0, (sym, pin, x)
        assert y % step == 0, (sym, pin, y)


@pytest.mark.parametrize("name", PLANTED)
def test_no_two_footprints_of_one_row_overlap(name: str) -> None:
    """Bodies never overlap; footprints of two cells of one column do not either."""
    prob = PLANTED[name]()
    cut = cut_of(prob)
    column_of = {
        c.sym: col.id for col in flow_of(prob).columns for ln in col.lanes for c in ln.cells
    }
    for page in placed_of(prob).pages:
        for a, b in combinations(page.placed, 2):
            assert not overlaps(a.body, b.body), (a.sym, b.sym)
            if column_of.get(a.sym) and column_of.get(a.sym) == column_of.get(b.sym):
                assert not overlaps(a.footprint, b.footprint), (a.sym, b.sym)
    assert cut.spec.pages


def _row_extent(prob: PlacementProblem) -> tuple[int, int]:
    """(placed extent, row_width) of the first row of the first page, justify off."""
    options = Options(marker=MARKER_BOX, justify=False)
    cut = cut_of(prob, options)
    env = page_envs(cut, prob, options)[0]
    spec = row_specs(env)[0]
    fps = footprints(placed_of(prob, options).pages[0])
    left = min(f.x for f in fps.values())
    return max(f.x + f.w for f in fps.values()) - left, row_width(spec)


@pytest.mark.parametrize("name", ["card_with_coils", "two_edge_card"])
def test_row_width_agrees_with_the_placed_extent(name: str) -> None:
    placed, measured = _row_extent(PLANTED[name]())
    assert placed == measured


def _respelled(prob: PlacementProblem) -> tuple[PlacementProblem, dict[str, str]]:
    maps = make_maps(id_sets(prob, flow_of(prob), blocks_of(prob)), "{:03d}")
    new = respell_problem(prob, maps)
    syms = tuple(replace(s, row_group="Z9" if s.row_group else None) for s in new.symbols)
    return replace(new, symbols=syms), maps


def _coords(placement: Placement, back: dict[str, str]) -> dict[str, object]:
    return {
        back[p.sym]: (p.x, p.y, p.orient, p.body, p.footprint, sorted(q.x + q.y for q in p.pin_xy))
        for page in placement.pages
        for p in page.placed
    }


def test_t4_a_row_group_of_plain_boxes_and_of_terminals_place_the_same() -> None:
    """Placement reads no id or group text: a respelled problem has the same coordinates."""
    prob = row_group_three("X1")
    new, maps = _respelled(prob)
    back = {v: k for k, v in maps.items()}
    assert _coords(placed_of(new), back) == _coords(placed_of(prob), {k: k for k in maps})


def test_placement_is_deterministic() -> None:
    for make in PLANTED.values():
        assert placed_of(make()) == placed_of(make())


def test_a_card_with_no_columns_is_placed() -> None:
    """layout-0283, layout-0288: a card block with no columns is placed in the row stage 4 gives."""
    prob = hub_shape()
    box = {p.sym: p for p in placed_of(prob).pages[0].placed}["K"]
    assert box.body.w > 0
    assert box.body.h > 0
    assert box.footprint.w >= box.body.w
