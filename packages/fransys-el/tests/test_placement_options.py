"""The placement conventions and the core options they pass on (E4)."""

import dataclasses
import typing
from dataclasses import replace

import pytest
from conventions_fixtures import LAYOUT, SHEET, house
from fransys_el import house_conventions
from fransys_el.placement_options import GENERAL, options
from fransys_el.placement_views import marker_boxes

from electrical_symbols import LIBRARY
from fransys_layout.core import Box, Options, Orientation, Size
from fransys_layout.symbols import outline_room


@pytest.mark.rule("SETTINGS")
def test_default_options_are_the_layout_toml_with_the_placement_conventions() -> None:
    """Every `[layout]` key reaches `Options` as written."""
    got = options(house(), LIBRARY)
    assert got.box_pins == "spread"
    assert got.bundle_direction is True
    assert got.pin_pairs == (("N", "S"),)
    for key, value in LAYOUT.items():
        if key in GENERAL:
            continue  # the conventions' own keys: test_the_general_keys_stay_out_of_the_core_options
        assert getattr(got, key) == (Size(*value) if key == "margin" else _tuple(value)), key


def _tuple(value: object) -> object:
    """A TOML list as nested tuples."""
    return tuple(_tuple(item) for item in value) if isinstance(value, list) else value


def test_the_marker_is_measured_from_the_library_symbol_at_all_eight_orientations() -> None:
    """The reference marker's keep-out box at R0 is 48 by 16 G; the other seven are measured."""
    marker = marker_boxes(LIBRARY)
    assert marker["R0"] == Box(0, -8, 48, 16)
    assert set(marker) == set(typing.get_args(Orientation))
    assert options(house(), LIBRARY).outline == outline_room(LIBRARY)
    given = replace(house().options, row_gap=9, outline=replace(outline_room(LIBRARY), margin=9))
    assert options(dataclasses.replace(house(), options=given), LIBRARY) == given


def test_replacing_one_option_moves_only_that_field() -> None:
    """Replacing `row_gap` in `house().options` changes exactly that field of the options."""
    base = options(house(), LIBRARY)
    moved = options(
        dataclasses.replace(house(), options=replace(house().options, row_gap=40)),
        LIBRARY,
    )
    changed = [field.name for field in dataclasses.fields(Options) if getattr(base, field.name) != getattr(moved, field.name)]
    assert changed == ["row_gap"]
    assert moved.row_gap == 40


@pytest.mark.rule("SETTINGS")
def test_the_general_keys_stay_out_of_the_core_options() -> None:
    """`step` and `pad` of `[layout]` are the table's own keys, never core options; the text room passed is the conventions' value."""
    got = house()
    assert got.text_height == 8
    assert house_conventions({**LAYOUT, "pad": 3}, LIBRARY, text_height=8, sheet=SHEET).options == got.options


def test_the_lane_step_is_the_library_wire_pitch() -> None:
    """The core's lane step (`wiring_grid`) follows `library.grid.wire_pitch`, never a literal."""
    wide = replace(LIBRARY, grid=replace(LIBRARY.grid, wire_pitch=16))
    assert options(house(), LIBRARY).wiring_grid == LIBRARY.grid.wire_pitch == 8
    assert options(house(), wide).wiring_grid == 16
