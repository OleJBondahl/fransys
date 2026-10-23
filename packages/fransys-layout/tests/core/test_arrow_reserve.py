"""The arrow reserve (layout-0301): a planned arrow at a row end keeps `Options.marker.w` free.

Plant: the box-riser problem of test_room_plants (one row, fans f:n1 and f:n2, f:n1's span ends at
x 1264; justify off, so the row's x do not move). A synthetic arrow of f:n1 leaves the right end.
"""

from __future__ import annotations

from dataclasses import replace

import pytest
from options_fixtures import core_options

from fransys_layout.core import Box, Facts, PlacementProblem
from fransys_layout.core.arrow_reserve import arrow_ends, reserve
from fransys_layout.core.place_env import page_envs
from fransys_layout.core.place_x import place_x, row_specs
from fransys_layout.core.place_y import _spans
from fransys_layout.core.values import Ref, RefEnd, RefKind

from .conftest import MARKER, MARKER_BOX
from .cut_fixtures import AREA, box_sym
from .flow_builders import net, poles
from .pipeline_fixtures import cut_of

OPTIONS = core_options(
    marker=MARKER,
    justify=False,
    flip_turn="R180",
    tag_stagger=True,
    label_gap=8,
    driver_first=True,
    arrow_sides=("E", "W"),
)
W = MARKER_BOX.w


def _env():
    syms = (box_sym(2), poles("L", 2), poles("M", 2))
    nets = (net("n1", "A1.p1", "L.n0", "M.n0"), net("n2", "A1.p2", "L.n1", "M.n1"))
    prob = PlacementProblem(AREA, syms, nets, facts=Facts())
    (env,) = page_envs(cut_of(prob, OPTIONS), prob, OPTIONS)
    return env


def _arrow(page: int, row: int) -> Ref:
    """An arrow of f:n1 leaving the right end of (page, row) and entering the next row's left."""
    return Ref(
        "f:n1", RefKind.ARROW, (RefEnd(page, None, None, row), RefEnd(page, None, None, row + 1))
    )


def test_the_reserve_is_the_marker_width_for_an_arrow_and_zero_without() -> None:
    assert (reserve(0, OPTIONS), reserve(1, OPTIONS), reserve(3, OPTIONS)) == (0, W, W)
    refs = (_arrow(1, 0),)
    assert arrow_ends(refs, 1, 0) == (0, 1)
    assert arrow_ends(refs, 1, 1) == (1, 0)
    assert arrow_ends(refs, 1, 0, "f:n2") == (0, 0)


def test_a_row_end_arrow_widens_the_row_and_the_fan_span_by_the_marker_width() -> None:
    """Expected: the right extent and f:n1 span end rise by marker.w; f:n2 and the x stay."""
    env = _env()
    x0, _ = place_x(env)
    base = {s.fan: s.x1 for s in _spans(env, x0)}
    wide = replace(env, refs=(_arrow(env.plan.page, 0),))
    x1, _ = place_x(wide)
    ends = {s.fan: s.x1 for s in _spans(wide, x1)}
    assert x1 == x0
    assert ends == {"f:n1": base["f:n1"] + W, "f:n2": base["f:n2"]}
    (before,), (after,) = row_specs(env), row_specs(wide)
    assert (before.tail_extra, after.tail_extra, after.lead_extra) == (0, W, 0)


def test_a_row_without_an_arrow_is_unchanged() -> None:
    env = _env()
    other = replace(env, refs=(_arrow(env.plan.page + 5, 0),))
    assert place_x(other) == place_x(env)
    assert [_spans(other, place_x(other)[0])] == [_spans(env, place_x(env)[0])]


def test_an_arrow_with_no_marker_box_is_refused_and_no_arrow_needs_none() -> None:
    assert (
        reserve(
            0,
            core_options(
                flip_turn="R180",
                tag_stagger=True,
                label_gap=8,
                driver_first=True,
                arrow_sides=("E", "W"),
            ),
        )
        == 0
    )
    with pytest.raises(ValueError, match=r"Options\.marker is unset"):
        reserve(
            1,
            core_options(
                flip_turn="R180",
                tag_stagger=True,
                label_gap=8,
                driver_first=True,
                arrow_sides=("E", "W"),
            ),
        )


def test_a_link_fit_box_sets_the_reserve_and_the_two_end_marker_boxes() -> None:
    """R350: the widest arrow's box is the reserve and the box of an arrow.

    A tag, star or stub keeps `Options.marker` (a stub's own fit is `marker_fit`'s)..
    """
    from turn_fixtures import marker_views

    from fransys_layout.core import PinRef
    from fransys_layout.core.geometry import marker_box_at

    wide = replace(OPTIONS, link_fit=marker_views(Box(0, -8, 60, 16)))
    assert reserve(1, OPTIONS) == W
    assert reserve(1, wide) == 60
    pin = PinRef("s", "p")
    assert marker_box_at(0, 0, wide, "R0", (pin, "arrow")).w == 60
    assert marker_box_at(0, 0, wide, "R0", (pin, "stub")).w == W
    assert marker_box_at(0, 0, wide, "R0", (pin, "tag")).w == W
