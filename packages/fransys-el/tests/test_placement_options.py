"""The placement conventions and the core options they pass on (E4)."""

import dataclasses
import typing
from dataclasses import replace

import pytest
from conventions_fixtures import LAYOUT, house
from fransys_el import house_conventions
from fransys_el.placement_options import GENERAL, options

from electrical_symbols import LIBRARY
from fransys_layout.core import Box, Options, Orientation, Size


@pytest.mark.rule("SETTINGS")
def test_default_options_are_the_layout_toml_with_the_placement_conventions() -> None:
    """Every `[layout]` key reaches `Options` as written; the marker is the library's."""
    got = options(house(), LIBRARY)
    assert got.box_pins == "spread"
    assert got.justify is True
    assert got.band_align is True
    assert got.bundle_direction is True
    assert got.justify_cards is False
    assert got.pin_pairs == (("N", "S"),)
    for key, value in LAYOUT.items():
        if key in GENERAL:
            continue  # the conventions' own keys: test_the_general_keys_reach_the_conventions
        assert getattr(got, key) == (Size(*value) if key == "margin" else _tuple(value)), key


def _tuple(value: object) -> object:
    """A TOML list as nested tuples."""
    return tuple(_tuple(item) for item in value) if isinstance(value, list) else value


def test_the_marker_is_measured_from_the_library_symbol_at_all_eight_orientations() -> None:
    """The reference marker's keep-out box at R0 is 48 by 16 G; the other seven are measured."""
    marker = options(house(), LIBRARY).marker
    assert marker is not None
    assert marker["R0"] == Box(0, -8, 48, 16)
    assert set(marker) == set(typing.get_args(Orientation))
    given = replace(house().options, marker={"R0": Box(1, 2, 3, 4)})
    assert options(dataclasses.replace(house(), options=given), LIBRARY) == given


def test_replacing_one_option_moves_only_that_field() -> None:
    """Replacing `row_gap` in `house().options` changes exactly that field of the options."""
    base = options(house(), LIBRARY)
    moved = options(
        dataclasses.replace(house(), options=replace(house().options, row_gap=40)),
        LIBRARY,
    )
    changed = [
        field.name
        for field in dataclasses.fields(Options)
        if getattr(base, field.name) != getattr(moved, field.name)
    ]
    assert changed == ["row_gap"]
    assert moved.row_gap == 40


def test_default_area_is_the_page_area() -> None:
    """The default page area is 1312 by 854."""
    assert house().area == Size(1312, 854)


@pytest.mark.rule("SETTINGS")
def test_the_general_keys_reach_the_conventions() -> None:
    """`area`, `text_height`, `step` and `pad` of `[layout]` are the conventions' values."""
    got = house()
    assert (got.area, got.text_height, got.step, got.pad) == (Size(1312, 854), 8, 8, 2)
    moved = house_conventions({**LAYOUT, "pad": 3, "area": [100, 50]}, LIBRARY)
    assert (moved.area, moved.pad) == (Size(100, 50), 3)


def test_the_lane_step_is_the_library_wire_pitch() -> None:
    """The core's lane step (`wiring_grid`) follows `library.grid.wire_pitch`, never a literal."""
    wide = replace(LIBRARY, grid=replace(LIBRARY.grid, wire_pitch=16))
    assert options(house(), LIBRARY).wiring_grid == LIBRARY.grid.wire_pitch == 8
    assert options(house(), wide).wiring_grid == 16
