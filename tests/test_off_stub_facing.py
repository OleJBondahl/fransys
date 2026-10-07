"""F1 part 3c: an off stub's stored `facing` is what render draws and what its arrow says.

Layout writes `LinkMarker.facing` (a compass side) on every off stub; render's
`marker_facing` reads it instead of re-deriving the direction from the placement's symbol,
and `off_stub_text` reads it for the arrow. Three checks, on laid-out models with off stubs
(the fixtures of `test_dd_units_stubs`): the stored facing agrees with the geometry render
would derive, turning the stored facing turns both the arrow and the drawn stub, and a
marker without a stored facing still takes the geometry.

Can-fail, checked by probe: `marker_facing` ignoring the stored facing (always returning
`geometry_facing`) fails the flip test for both the N and the S case.
"""

import dataclasses
import functools
import importlib.util
from pathlib import Path

import pytest
from fransys_render import pages as render_pages
from fransys_render._markers import (
    _shared_box_glyph,
    geometry_facing,
    marker_facing,
    stub_end,
)
from fransys_render._numbers import format_decimal, grid_to_mm

from fransys_model.derive import draws_as_line
from fransys_model.derive.drawing_text import off_stub_text
from fransys_model.kernel import Origin, evolve
from fransys_model.layout import LinkMarker, Page, Side, StarKind, layout_of, sheet_format_of

_ORIGIN = Origin(file="tests/test_off_stub_facing.py", line=1, note="facing flip")
_OPPOSITE = {Side.N: Side.S, Side.S: Side.N, Side.E: Side.W, Side.W: Side.E}


def _load(name: str):
    """A sibling root test module, loaded by path (root tests are not a package)."""
    spec = importlib.util.spec_from_file_location(name[:-3], Path(__file__).with_name(name))
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_OFF_STUB = _load("test_unit_boundary_off_stub.py")
_SYSTEM = _load("test_units_worked_example.py")
_STUBS = _load("test_dd_units_stubs.py")


@functools.cache
def _models():
    """Every laid-out model with off stubs: N-facing in all, S-facing in the system one."""
    return {
        "boundary": _OFF_STUB._build().model,
        "system": _SYSTEM._build_system()[0].model,
        "two_location": _STUBS._two_location_cable_model(),
        "two_connectors": _STUBS._build_two_connectors(relay_between=True),
    }


def _off_stubs(model):
    found = [m for m in layout_of(model, LinkMarker).values() if m.star is StarKind.OFF]
    return sorted(found, key=lambda m: m.id)


def _is_line_stub(model, marker) -> bool:
    """HL18: a leaving line's stub stands at the line's end, not at a port."""
    return marker.carrier is not None and draws_as_line(model, marker.carrier)


@pytest.mark.parametrize(
    ("name", "only_lines"),
    [("boundary", True), ("system", False), ("two_location", True), ("two_connectors", True)],
)
def test_the_stored_facing_agrees_with_the_geometry_render_derives(name, only_lines) -> None:
    """Every off stub stores its facing; a stub at a port agrees with the port's geometry.

    A line stub (HL18) has no port geometry to agree with, so only its stored facing is checked.
    """
    model = _models()[name]
    stubs = _off_stubs(model)
    assert stubs
    at_ports = [m for m in stubs if not _is_line_stub(model, m)]
    assert (at_ports == []) is only_lines
    for marker in stubs:
        assert marker.facing is not None
    for marker in at_ports:
        assert geometry_facing(model, marker).name == marker.facing.name


def _the_stub_line(model, marker) -> str:
    """The `<line class="marker">` render draws for `marker`, as its SVG text.

    A line stub draws no stub, its line runs on to the box (layout-0158): its box, then.
    """
    page = layout_of(model, Page)[marker.page]
    sheet = sheet_format_of(model, page.sheet_format)
    if _is_line_stub(model, marker):
        return _shared_box_glyph(sheet, marker, marker_facing(model, marker))
    end_x, end_y = stub_end(marker, marker_facing(model, marker))

    def mm(origin, grid):
        return format_decimal(grid_to_mm(origin, grid, sheet.module_mm))

    return (
        f'<line class="marker" x1="{mm(sheet.content_x_mm, marker.x)}" '
        f'y1="{mm(sheet.content_y_mm, marker.y)}" x2="{mm(sheet.content_x_mm, end_x)}" '
        f'y2="{mm(sheet.content_y_mm, end_y)}"/>'
    )


def _svg_of(model, marker) -> str:
    page = marker.page
    return render_pages(model)[f"{page.kind}:{page.value}"]


@pytest.mark.parametrize(
    ("name", "facing", "arrow", "flipped_arrow"),
    [("boundary", Side.N, "←", "→"), ("system", Side.S, "→", "←")],
)
def test_turning_the_stored_facing_turns_the_arrow_and_the_drawn_stub(
    name, facing, arrow, flipped_arrow
) -> None:
    model = _models()[name]
    marker = next(m for m in _off_stubs(model) if m.facing is facing)
    flipped = dataclasses.replace(marker, facing=_OPPOSITE[facing])
    flipped_model = evolve(model, remove=[marker.id], put=[flipped], origin=_ORIGIN)

    assert f" {arrow} " in f" {off_stub_text(model, marker)} "
    assert f" {flipped_arrow} " in f" {off_stub_text(flipped_model, flipped)} "

    # the stub render draws follows: the far end lands on the other side of the port
    before = stub_end(marker, marker_facing(model, marker))
    after = stub_end(flipped, marker_facing(flipped_model, flipped))
    assert (before[0] - marker.x, before[1] - marker.y) == (
        -(after[0] - marker.x),
        -(after[1] - marker.y),
    )
    assert before != after
    line, flipped_line = _the_stub_line(model, marker), _the_stub_line(flipped_model, flipped)
    assert line in _svg_of(model, marker)
    assert flipped_line in _svg_of(flipped_model, flipped)
    assert line not in _svg_of(flipped_model, flipped)


def test_a_marker_without_a_stored_facing_takes_the_geometry_facing() -> None:
    """No fixture lays out a page-boundary marker, so an off stub is turned into a plain one.

    The stub is one at a port: a line stub (HL18) has no port geometry."""
    model = _models()["system"]
    stub = next(m for m in _off_stubs(model) if not _is_line_stub(model, m))
    plain = dataclasses.replace(stub, star=None, far=None, carrier=None, facing=None)
    plain_model = evolve(model, remove=[stub.id], put=[plain], origin=_ORIGIN)
    assert marker_facing(plain_model, plain) is geometry_facing(plain_model, plain)
    assert marker_facing(plain_model, plain).name == stub.facing.name
