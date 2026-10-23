"""`solve` lays again where an anchored outline missed; `solve_rounds` bounds it (POWER-NET)."""

from __future__ import annotations

from dataclasses import replace

import pytest
from options_fixtures import core_options

from fransys_layout.core.anchors import anchor_misses
from fransys_layout.core.solve import solve
from fransys_layout.core.values import Anchor, Box, PinRef, Pose
lazy from fransys_layout.core import CoreLayout, Options, PlacementProblem

from .conftest import MARKER
from .values_fixtures import problem


def _options(rounds: int) -> Options:
    return core_options(
        marker=MARKER,
        tag_stagger=True,
        flip_turn="R180",
        label_gap=8,
        driver_first=True,
        arrow_sides=("E", "W"),
        solve_rounds=rounds,
    )


def _problem() -> PlacementProblem:
    """The card K1 with a 16-wide outline 40 left of its N pin, which the first layout misses."""
    outline = Box(-40, 0, 16, 32)
    anchor = Anchor(PinRef("K1", "1"), (("N", Pose("R90", (-40, 0), outline, (-40, 0))),))
    return replace(problem(), anchors=(anchor,))


def _layout(rounds: int) -> CoreLayout:
    return solve(_problem(), _options(rounds))


def _misses(layout: CoreLayout) -> tuple[object, ...]:
    """The anchored outlines the layout leaves meeting a body, an outline or the frame."""
    return anchor_misses(layout.placement, layout.annotations.anchored, _problem(), _options(0))


@pytest.mark.rule("POWER-NET")
def test_a_missed_outline_is_held_by_a_second_layout() -> None:
    assert _misses(_layout(3)) == ()


@pytest.mark.rule("POWER-NET")
def test_with_no_further_round_the_same_outline_overlaps() -> None:
    assert _misses(_layout(0)) != ()
