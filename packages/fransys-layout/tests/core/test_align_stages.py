"""Stage 5 end to end with bands, mates and trunks: the placed pins, read from the Placement."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from options_fixtures import core_options

from fransys_layout.core import Facts

from . import align_fixtures as fx
from .conftest import MARKER
from .pipeline_fixtures import placed_of
from .place_fixtures import all_pins

if TYPE_CHECKING:
    from fransys_layout.core import Placement

GRID = core_options(
    marker=MARKER,
    flip_turn="R180",
    tag_stagger=True,
    label_gap=8,
    parallel_pitch=48,
    driver_first=True,
    arrow_sides=("E", "W"),
).wiring_grid


def _origins(pl: Placement) -> dict[str, int]:
    return {p.sym: p.y for page in pl.pages for p in page.placed}


def test_bands_align_through_the_stages() -> None:
    """Rank 1 and rank 2 cells of the two columns stand at one y each; unheld, they do not."""
    prob = fx.two_band_columns()
    held, free = (
        placed_of(prob),
        placed_of(
            prob,
            core_options(
                marker=MARKER,
                band_align=False,
                flip_turn="R180",
                tag_stagger=True,
                label_gap=8,
                parallel_pitch=48,
                driver_first=True,
                arrow_sides=("E", "W"),
            ),
        ),
    )
    y, y_free = _origins(held), _origins(free)
    assert held.findings == ()
    assert y["a1"] == y["b1"]
    assert y["a2"] == y["b2"]
    assert y_free["a1"] != y_free["b1"]
    assert y_free["a2"] != y_free["b2"]


def test_mated_pins_share_a_y_through_the_stages() -> None:
    """p.s and q.n meet at one y, read from the placed pins; without the mate they differ."""
    prob = fx.mate_columns()
    held = all_pins(placed_of(prob))
    free = all_pins(placed_of(replace(prob, facts=Facts())))
    assert held[("p", "s")][1] == held[("q", "n")][1]
    assert free[("p", "s")][1] != free[("q", "n")][1]


def test_a_band_against_a_trunk_is_dropped_through_the_stages() -> None:
    held = placed_of(fx.band_against_trunk("X1"))
    y = _origins(held)
    assert [(f.code, f.page) for f in held.findings] == [("ALIGN_DROPPED", 1)]
    assert "band" in held.findings[0].text
    assert y["h"] != y["l2"]
    assert y["u1"] == y["v1"]
    free = _origins(placed_of(fx.band_against_trunk(None)))
    assert free["u1"] != free["v1"]


def test_every_pin_stays_on_the_wiring_grid() -> None:
    for build in (fx.two_band_columns, fx.mate_columns, lambda: fx.band_against_trunk("X1")):
        pins = all_pins(placed_of(build()))
        assert pins
        assert all(y % GRID == 0 for _, y in pins.values())
