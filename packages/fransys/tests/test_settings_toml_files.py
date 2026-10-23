"""The shipped TOML settings hold today's constant values (settings spec ST1, ST2)."""

import tomllib
from dataclasses import fields
from pathlib import Path

import fransys
from fransys_el import REF_TINTS

import fransys_layout
from fransys_layout.core import Options
from fransys_model.layout import SheetFormat, a2_sheet_format, default_sheet_format

# Options fields with no TOML home yet: no home, a nested dataclass, a callable or None.
LEFT_OUT = {
    "flip_turn",
    "driver_first",
    "bundle_direction",
    "arrow_sides",
    "wiring_grid",
    "marker",
    "marker_fit",
    "link_fit",
    "marker_vertical",
    "marker_above",
    "marker_below",
    "wire_label_sides",
}
# The general `[layout]` keys the el conventions take: page area and text values (R338 phase 2).
GENERAL = {"area", "text_height", "step", "pad", "contact_tables"}
SHEET_DROPPED = {"id", "key", "module_mm", "ext"}


def _toml_value(value: object) -> object:
    """A tuple as the list TOML reads it back as; every other value as it is."""
    return list(value) if isinstance(value, tuple) else value


def _sheet_table(sheet: SheetFormat) -> dict[str, object]:
    """A sheet's fields as the settings file keeps them."""
    return {f.name: getattr(sheet, f.name) for f in fields(sheet) if f.name not in SHEET_DROPPED}


LAYOUT_VALUES = {
    "area": [1312, 854],
    "text_height": 8,
    "step": 8,
    "pad": 2,
    "contact_tables": False,
    "margin": [16, 16],
    "wire_min": 8,
    "column_gap_min": 8,
    "row_gap": 24,
    "box_pin_pitch_min": 16,
    "box_pins": "spread",
    "short_height": 0.4,
    "min_fill": 0.25,
    "exact_order_limit": 12,
    "exact_order_nodes": 50000,
    "tag_stagger": True,
    "justify": True,
    "justify_cards": False,
    "pin_pairs": [["N", "S"]],
    "band_align": True,
    "w_tag": 1.0,
    "w_arrow": 0.5,
    "w_ref": 3.0,
    "w_p": 2.0,
    "w_f": 1.0,
    "w_row": 0.05,
    "w_violation": 1000000.0,
    "bend_penalty": 19,
    "crossing_penalty": 64,
    "box_margin": 16,
    "column_wire_lanes": 3,
    "jog_lanes": 2,
    "spare_cells": 3,
    "reroute_rounds": 3,
    "recut_rounds": 3,
    "solve_rounds": 3,
    "corner_order": ["TL", "BL", "BR", "TR"],
    "slack": [0, 8, 16],
    "cells": [8, 6],
    "label_gap": 8,
    "open_stub": 0,
    "box_columns": True,
    "wrap_wide_fans": True,
    "top_headroom_lanes": 3,
    "bottom_headroom_lanes": 1,
    "end_bias_weight": 3,
}


def test_layout_toml_holds_todays_values() -> None:
    """Every `[layout]` value is today's: a moved value is a visible change and needs its Rule."""
    path = Path(fransys_layout.__file__).parent / "layout.toml"
    assert tomllib.loads(path.read_text(encoding="utf-8")) == {"layout": LAYOUT_VALUES}


def test_layout_toml_keys_are_options_fields() -> None:
    """Every key of `layout.toml` is an `Options` field, and every size field has a key."""
    path = Path(fransys_layout.__file__).parent / "layout.toml"
    keys = set(tomllib.loads(path.read_text(encoding="utf-8"))["layout"])
    names = {f.name for f in fields(Options)}
    assert keys - names == GENERAL
    keys -= GENERAL
    assert keys <= names
    assert names - keys == LEFT_OUT


def test_settings_toml_matches_constants() -> None:
    path = Path(fransys.__file__).parent / "settings.toml"
    expected = {
        "paper": {
            "default": "A3",
            "formats": {
                "A3": _sheet_table(default_sheet_format()),
                "A2": _sheet_table(a2_sheet_format()),
            },
        },
        "look": {"ref_tints": list(REF_TINTS)},
    }
    loaded = tomllib.loads(path.read_text(encoding="utf-8"))
    assert {"paper": loaded["paper"], "look": loaded["look"]} == expected
