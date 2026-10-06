"""The records above row 0 stay inside the content box with the shipped headroom lanes
(layout-0031), and with none (S20 M4's top reference band).

`packages/fransys-layout/tests/engines/test_top_headroom.py` shows the cabinet is clean with no
lanes, because the band lifts the first row. A unit outline stands close above the first row's
keep-out; the system model's outlines are inside the content box with no lanes too, because the
band is taller than the outline's margin.

Since layout-0080 a top-level unit's boundary connector wired to a same-location plug is a stub at
each end, not a route turning above row 0, so the smallest fixture stays inside the content box
even with no lanes.

Fixtures: `test_units_worked_example._top_level_boundary_to_unitless_probe_model` (the smallest:
one boundary connector wired to one unitless plug, two stubs and no route) and
`test_units_worked_example._build_system` (two pump cabinets and two board units, four outlines).
"""

import functools
import importlib.util
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from fransys_layout.engines.schematic import engine, run_stages
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.geometry import WIRING_GRID
from fransys_layout.lint.codes import OUT_OF_CONTENT_BOX, WIRE_OVER_LABEL
from fransys_layout.stages.route import ROUTE_FAILED

if TYPE_CHECKING:
    from fransys_layout.stages import Layout
    from fransys_model.kernel import Model

_FAILURES = {ROUTE_FAILED, WIRE_OVER_LABEL, OUT_OF_CONTENT_BOX}


@functools.cache
def _worked_example():
    """The sibling root test module, loaded by path (root tests are not a package)."""
    path = Path(__file__).with_name("test_units_worked_example.py")
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@functools.cache
def _top_level_model() -> Model:
    return _worked_example()._top_level_boundary_to_unitless_probe_model()


@functools.cache
def _system_model() -> Model:
    return _worked_example()._build_system()[0].model


def _run(
    model: Model, monkeypatch: pytest.MonkeyPatch, lanes: int | None
) -> tuple[Layout, set[str]]:
    """The layout and finding codes of `model`, with `lanes` headroom lanes (None: as shipped).

    `engine` imports the constant by name, so the patch goes on `engine`, not on `defaults`.
    """
    if lanes is not None:
        monkeypatch.setattr(engine, "TOP_HEADROOM_LANES", lanes)
    layout, _, findings = run_stages(model, read_inputs(model))
    return layout, {finding.code for finding in findings}


def _highest_top(layout: Layout) -> int:
    """The smallest y of any keep-out, label or marker box, route vertex or outline."""
    return min(
        (
            *(one.at.y + one.geometry.keepout.y for one in layout.placed),
            *(label.box.y for label in layout.labels),
            *(marker.box.y for marker in layout.markers),
            *(point.at.y for route in layout.routes for point in route.points),
            *(outline.box.y for outline in layout.outlines),
        )
    )


@pytest.mark.parametrize("model_of", [_top_level_model, _system_model])
def test_the_shipped_headroom_keeps_every_record_inside_the_content_box(
    model_of, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Row 0 starts below the shipped lanes: no route failure, wire over a label or box leaving the
    content box, and every keep-out, text, route vertex and outline is at y >= 0."""
    # UNDO: stages/place.py `_stack_page`: `band = 0`, and engines/schematic/defaults.py
    #     `TOP_HEADROOM_LANES = 0` (the system model's outlines then stand at y = -2)
    layout, codes = _run(model_of(), monkeypatch, None)
    assert not codes & _FAILURES
    # something is drawn (not vacuous): routes (the system model), or the off stubs that end a
    # top-level unit's boundary wire (the smallest model has no route since layout-0080)
    assert layout.routes or any(marker.star == "off" for marker in layout.markers)
    assert layout.outlines
    top = _highest_top(layout)
    assert top >= 0  # nothing stands above the content box
    assert top <= 4 * WIRING_GRID  # and the first row still starts near it


def test_without_headroom_the_unit_outlines_stay_below_the_top_reference_band(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """S20 M4: with no lane the outlines of the first row still stand inside the content box,
    because the columns start below the top band every page keeps. (Before M4 the outlines of
    this model stood above the box top with no lane: the constant is no longer what holds them.)
    """
    # UNDO: stages/place.py `_stack_page`: `band = reference_band(sheet, profile)` -> `band = 0`
    #     (the system model's outlines then stand at y = -2, above the content box)
    layout, _ = _run(_system_model(), monkeypatch, 0)
    assert len(layout.outlines) == 4
    assert min(outline.box.y for outline in layout.outlines) >= 0
