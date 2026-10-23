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
    "parallel_pitch": 48,
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


def _table(name: str) -> dict[str, object]:
    """One table of the shipped `settings.toml`."""
    path = Path(fransys.__file__).parent / "settings.toml"
    return tomllib.loads(path.read_text(encoding="utf-8"))[name]


def test_reference_toml_holds_todays_values() -> None:
    expected = {
        "page_prefix": "p",
        "cell_sep": ":",
        "location_sign": "+",
        "set_sep": ".",
        "width_sample": "/99.99",
    }
    assert _table("reference") == expected


def test_frame_toml_holds_todays_values() -> None:
    expected = {"row_labels": "letters", "column_labels": "numbers", "row_order": "top_down"}
    assert _table("frame") == expected


def test_stub_toml_holds_todays_values() -> None:
    expected = {"arrow_in": "←", "arrow_out": "→", "port_sep": ":", "port_join": " "}
    assert _table("stub") == expected


def test_wire_label_toml_holds_todays_values() -> None:
    expected = {"separator": " ", "show_ends": True}
    assert _table("wire_label") == expected


def test_harness_toml_holds_todays_values() -> None:
    expected = {"branch_sep": "."}
    assert _table("harness") == expected


def test_colours_toml_holds_todays_values() -> None:
    expected = {
        "pe": "GNYE",
        "shield": "SH",
        "defaults": {
            "AC_L1": ["BK", ""],
            "AC_L2": ["BK", ""],
            "AC_L3": ["BK", ""],
            "AC_N": ["BU", ""],
            "AC_CONTROL": ["RD", ""],
            "DC_SUPPLY": ["BU", ""],
            "DC_CONTROL": ["BU", ""],
            "DC_GROUND": ["BU", ""],
            "DC_SIGNAL": ["BU", ""],
        },
    }
    assert _table("colours") == expected


def test_title_block_toml_holds_todays_values() -> None:
    expected = {
        "fields": [
            "title",
            "number",
            "revision",
            "revision_date",
            "customer",
            "author",
            "page_title",
            "scope",
            "sheet",
            "page",
        ],
        "band_mm": 20.0,
        "centre_gap_mm": 3.125,
    }
    assert _table("title_block") == expected


def test_revision_table_toml_holds_todays_values() -> None:
    expected = {
        "columns": ["revision", "date", "description", "created", "checked", "approved"],
        "description_mm": 120.0,
    }
    assert _table("revision_table") == expected


def test_revision_toml_holds_todays_values() -> None:
    expected = {
        "date_format": "YYYY-MM-DD",
        "initials_required": True,
        "format": "{version}.{revision}",
    }
    assert _table("revision") == expected


def test_words_toml_holds_todays_values() -> None:
    expected = {
        "side_a": "Side A",
        "side_b": "Side B",
        "wire_from": "from",
        "pin": "Pin",
        "mate": "Mate",
        "designation": "Designation",
        "mpn": "MPN",
        "description": "Description",
        "cores": "Cores",
        "gauge": "Gauge",
        "length_mm": "Length mm",
        "ends": "Ends",
        "spare": "spare",
        "signal_di": "DI",
        "signal_do": "DO",
        "signal_ai_ma": "AI (mA)",
        "signal_ai_v": "AI (V)",
        "signal_ao_ma": "AO (mA)",
        "signal_ao_v": "AO (V)",
        "signal_rtd": "RTD",
        "signal_relay_do": "DO (relay)",
        "no": "NO",
        "nc": "NC",
        "title": "Title",
        "number": "Number",
        "revision": "Revision",
        "revision_date": "Revision date",
        "customer": "Customer",
        "author": "Author",
        "page_title": "Page title",
        "scope": "Scope",
        "sheet": "Sheet",
        "page": "Page",
        "block_diagram": "Block diagram",
        "schematic": "Schematic",
        "harness_drawing": "Harness drawing",
        "cover": "Cover",
        "notes": "Notes",
        "sheets": "Sheets",
        "contents": "Contents",
        "plc_list": "PLC list",
        "terminal_list": "Terminal list",
        "connector_list": "Connector list",
        "wire_label_list": "Wire label list",
        "designation_list": "Designation list",
        "cable_list": "Cable list",
        "bom": "BOM",
        "cabinet_schematic": "Cabinet schematic",
        "pcb_schematic": "PCB schematic",
        "system": "System",
        "continued": "(cont.)",
        "range_word": "to",
        "and_word": "and",
        "more_word": "more",
        "list_join": ", ",
        "bullet": "• ",
        "numbered": "{i}. ",
        "ellipsis": "…",
        "bridge": "Bridge",
        "date": "Date",
        "created": "Created",
        "checked": "Checked",
        "approved": "Approved",
    }
    assert _table("words") == expected
