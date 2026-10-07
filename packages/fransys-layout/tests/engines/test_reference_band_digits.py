"""SET-DIGITS: the room `place` reserves for a reference is no narrower than its drawn box.

The band (`place._reference_band`) and the box (`reference_box_width`) are sized from the same
set's `Digits` (layout-0135). A run of several sets prints `p<set>.<page>` and `+<location>`
forms, so a box wider than the two-digit floor must not stand in a narrower band.
"""

import sys
from collections import defaultdict
from functools import cache
from importlib import import_module
from typing import Any
from unittest.mock import patch

import pytest
from layout_cabinet import build_cabinet

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.geometry import WIRING_GRID
from fransys_layout.stages.references.digits import FLOOR
from fransys_model.kernel import freeze


@cache
def _run(cabinet: str) -> tuple[dict[int, int], dict[int, int]]:
    """Per drawing set: the narrowest band `place` reserved, and the width of its drawn box."""
    model = freeze(build_cabinet(second_location=cabinet == "two_location"))
    bands: dict[int, list[int]] = defaultdict(list)
    place = import_module("fransys_layout.stages.place")  # `stages.place` names the function
    real = place._reference_band

    def spy(sheet: Any, profile: Any, digits: Any = FLOOR) -> int:
        band = real(sheet, profile, digits)
        bands[sys._getframe(1).f_locals["plan"].drawing_set].append(band)
        return band

    with patch.object(place, "_reference_band", spy):
        results, _ = stage_results(model, read_inputs(model))
    # a reference box stands turned at an N or S port: its long side is the box's width
    widths = {
        one.drawing_set: max(one.box.width, one.box.height)
        for one in results.layout.markers
        if one.star != "off"
    }
    return {one: min(found) for one, found in bands.items()}, widths


@pytest.mark.parametrize("cabinet", ["one_location", "two_location"])
def test_the_reserved_band_holds_every_sets_drawn_reference_box(cabinet: str) -> None:
    """Each set's band is at least a stub's clearance plus the box that set draws.

    CAN-FAIL: place.py `_reference_band`: size it by `FLOOR` (no `digits`), and a set whose
    box is wider than the floor's has a narrower band than its box.
    """
    bands, widths = _run(cabinet)
    assert widths
    assert set(widths) <= set(bands)
    for one, width in widths.items():
        assert bands[one] >= WIRING_GRID + width, one


def test_a_run_of_several_sets_draws_a_box_wider_than_the_floor() -> None:
    """Guard: the test above is not vacuous; the two-location cabinet draws past the floor."""
    _, widths = _run("two_location")
    _, one_set = _run("one_location")
    assert widths[1] > one_set[1]


def test_the_page_side_rooms_carry_the_sets_digits_the_early_call_keeps_the_floor() -> None:
    """layout-0135 (a): the pre-plan call sizes columns at FLOOR; each page's call is its set's.

    CAN-FAIL: pagerun `_page_boxes`: build `Wiring` without `page.digits`, and no per-page call
    carries a width past the floor.
    """
    pagerun = import_module("fransys_layout.stages.pagerun")
    engine = import_module("fransys_layout.engines.schematic.engine")
    model = freeze(build_cabinet(second_location=True))
    calls: dict[str, list[Any]] = {"engine": [], "page": []}

    def watch(where: str, module: Any):
        real = module.side_reference_rooms

        def spy(columns: Any, drawn: Any, wiring: Any, **kwargs: Any) -> Any:
            calls[where].append(wiring.digits)
            return real(columns, drawn, wiring, **kwargs)

        return patch.object(module, "side_reference_rooms", spy)

    with watch("engine", engine), watch("page", pagerun):
        stage_results(model, read_inputs(model))
    assert calls["engine"]
    assert set(calls["engine"]) == {FLOOR}
    assert any(one != FLOOR for one in calls["page"])
