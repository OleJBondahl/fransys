"""cut_height: the cut's height estimate holds the fitted marker boxes of a column (R508)."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from options_fixtures import core_options

from fransys_layout.core import Box, PinRef
from fransys_layout.core.cut_height import lowered
from fransys_layout.core.flow_values import Cell, Column, Lane
lazy from fransys_layout.core.values import Options

from .conftest import MARKER

COLUMN = Column("c", (Lane((Cell("A", "R0", "a1", "a2"),), 0),), (), (), 100, 16)


def _options(fit: dict[Any, Any]) -> Options:
    base = core_options(
        marker=MARKER,
        justify=False,
    )
    return replace(base, marker_fit=fit, marker_vertical=frozenset({"R90"}))


def test_a_fitted_head_box_adds_its_reach_up_and_a_foot_box_its_reach_down() -> None:
    fit = {
        (PinRef("A", "a1"), "tag"): {"R90": Box(-6, -30, 12, 30)},
        (PinRef("A", "a2"), "tag"): {"R90": Box(-6, 0, 12, 40)},
    }
    assert lowered(100, [COLUMN], _options(fit)) == 170


def test_no_fit_and_a_fit_equal_to_the_plain_marker_add_nothing() -> None:
    assert lowered(100, [COLUMN], _options({})) == 100
    same = {(PinRef("A", "a1"), "tag"): MARKER}
    assert lowered(100, [COLUMN], _options(same)) == 100


def test_no_columns_add_nothing() -> None:
    assert lowered(100, [], _options({})) == 100
