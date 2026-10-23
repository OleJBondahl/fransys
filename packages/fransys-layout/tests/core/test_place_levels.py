"""Trunk levels: nine overlapping trunks of one row and side take one order however ids read."""

from __future__ import annotations

import pytest
from options_fixtures import core_options

from fransys_layout.core import natural_key
from fransys_layout.core.constraints import Graph
from fransys_layout.core.place_levels import EXACT_LIMIT, Span, trunk_levels
from fransys_layout.core.place_trunk import trunk_node

# (fan, x0, x1, driver xs, leg xs): nine trunks overlapping in a chain; f10 sorts before f2.
TRUNKS = (
    ("f2", 82, 474, (), (410,)),
    ("f3", 12, 180, (36, 100), (20, 140)),
    ("f4", 54, 213, (), (158,)),
    ("f5", 17, 228, (), (25, 121)),
    ("f6", 144, 325, (), (288, 304)),
    ("f7", 15, 312, (39, 215), ()),
    ("f8", 11, 303, (), (219,)),
    ("f9", 36, 324, (), (188, 316)),
    ("f10", 174, 370, (), (318, 334)),
)


def levels(spelled: dict[str, str]) -> list[str]:
    """The fans from the top level down, spelled as `spelled` says."""
    spans = [Span(spelled[f], 0, a, b, 1, "S", d, leg) for f, a, b, d, leg in TRUNKS]
    g = Graph()
    for s in spans:
        g.add(trunk_node(s.fan, 0))
    trunk_levels(
        g,
        spans,
        core_options(
            flip_turn="R180",
            tag_stagger=True,
            label_gap=8,
            parallel_pitch=48,
            driver_first=True,
            arrow_sides=("E", "W"),
        ),
    )
    y = g.solve()
    assert y is not None
    return sorted((s.fan for s in spans), key=lambda f: y[trunk_node(f, 0)])


@pytest.mark.parametrize("form", ["{}", "T{:04d}"])
def test_nine_overlapping_trunks_do_not_depend_on_how_fan_ids_are_spelled(form: str) -> None:
    assert len(TRUNKS) > EXACT_LIMIT  # the greedy order runs: it breaks ties by natural fan order
    ranked = sorted((t[0] for t in TRUNKS), key=natural_key)
    spelled = {f: form.format(n) for n, f in enumerate(ranked, 1)}
    same = {f: f for f, *_ in TRUNKS}
    assert levels(spelled) == [spelled[f] for f in levels(same)]
