"""The overview page on the units worked example (OVERVIEW A1, A3, A4; O22).

The page draws the recorded positions of every view and prints the rows' texts. Each test names
what breaks it.
"""

import json
import re
import sys
from functools import cache
from pathlib import Path
from typing import Any

import fransys as fr
import fransys_parts
from _model_build_cover import system_document
from fransys_overview import html
from fransys_overview._app import APP_JS

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_units_worked_example import _system_design

from fransys_layout.engines.overview import lay_out_overview
from fransys_model.derive import (
    overview_tree,
    overview_units,
    overview_view_rows,
    printed_designation,
    reference_designation,
)
from fransys_model.derive.block_diagram import box_lines, diagram_lines
from fransys_model.layout import OverviewBox, OverviewLine, OverviewView, layout_of


@cache
def _laid() -> tuple[Any, str]:
    parts = fransys_parts.load("demo_parts")
    design, _field1, _field2 = _system_design(parts)
    model = fr.build(parts, design.draft(), system_document()).model
    out = lay_out_overview(model)[0]
    return out, html(out)


def _data() -> dict[str, Any]:
    found = re.search(r'id="overview-data">(.*?)</script>', _laid()[1], re.DOTALL)
    assert found is not None
    return json.loads(found.group(1))


def test_the_page_holds_every_recorded_view() -> None:
    """A4: breaks if a view with records is dropped from the data."""
    views = layout_of(_laid()[0], OverviewView)
    assert len(views) > 5
    assert len(_data()["views"]) == len(views)


def test_every_view_the_rows_name_has_records() -> None:
    """The engine and the page read the same rows: breaks if the engine skips a view."""
    out = _laid()[0]
    rows = [r for unit in overview_units(out) for r in overview_view_rows(out, unit)]
    assert len(rows) == len(layout_of(out, OverviewView))


def test_the_page_holds_each_recorded_position() -> None:
    """A4: breaks if a box, tab or line vertex is moved, dropped or recomputed in the page."""
    out = _laid()[0]
    boxes = list(layout_of(out, OverviewBox).values())
    lines = list(layout_of(out, OverviewLine).values())
    page_boxes = [b for v in _data()["views"] for b in v["boxes"]]
    page_lines = [ln for v in _data()["views"] for ln in v["lines"]]
    assert sorted((b["x"], b["y"], b["w"], b["h"]) for b in page_boxes) == sorted(
        (b.x, b.y, b.width, b.height) for b in boxes
    )
    assert sorted((t[0], t[1], t[2]) for b in page_boxes for t in b["tabs"]) == sorted(
        (t.x, t.y, t.text_width) for b in boxes for t in b.tabs
    )
    assert sorted(map(tuple, (p for ln in page_lines for p in ln["pts"]))) == sorted(
        (p.x, p.y) for ln in lines for p in ln.points
    )
    assert len(page_lines) == len(lines)


def test_the_page_script_runs_no_layout() -> None:
    """A4: breaks if the script places anything itself."""
    assert not re.search(r"\blayout\b", APP_JS)
    assert "'preset'" not in APP_JS


def _system_view() -> dict[str, Any]:
    (view,) = (
        v
        for v in _data()["views"]
        if v["unit"] is None and v["mode"] == "plain" and v["open"] is None
    )
    return view


def test_the_system_level_prints_the_block_diagram_rows() -> None:
    """A1 at page level: the system view's lines and boxes are the block diagram's rows."""
    out = _laid()[0]
    rows = diagram_lines(out, None)
    view = _system_view()
    assert sorted(ln["text"] for ln in view["lines"]) == sorted(r.designation for r in rows)
    reached = {box for row in rows for box in (row.a, row.b)}
    assert {tuple(b["lines"]) for b in view["boxes"]} == {
        box_lines(out, box, None) for box in reached
    }


def test_no_carrier_inside_an_opened_unit_is_printed_absolute() -> None:
    """A3 at page level: a unit view prints a cable as the unit's own list does (`-W1`)."""
    out = _laid()[0]
    page = {
        (v["unit"], v["mode"]): v
        for v in _data()["views"]
        if v["level"] is None and v["open"] is None
    }
    units = [u for u in overview_units(out) if u]
    differs = checked = 0
    for unit in units:
        for rows in overview_view_rows(out, unit):
            if rows.open is not None or rows.level is not None:
                continue
            texts = [ln.text for ln in rows.lines]
            assert texts == [ln["text"] for ln in page[units.index(unit), rows.mode.value]["lines"]]
            for line in (ln for ln in rows.lines if ln.via is not None):
                assert line.via is not None
                relative = printed_designation(out, line.via, unit=unit)
                checked += 1
                assert line.text == relative
                differs += relative != reference_designation(out, line.via)
    assert checked
    assert differs


def test_the_parts_tree_prints_the_rows_derive_gives() -> None:
    """O12, O22: breaks if the page names a tree row itself or drops a unit's rows."""
    out = _laid()[0]
    rows = overview_tree(out)
    tree = _data()["tree"]
    assert [t["label"] for t in tree] == [r.label for r in rows]
    assert [t["parent"] for t in tree] == [r.parent for r in rows]
    assert any(t["is_unit"] for t in tree)


def test_the_features_panel_names_every_switch_and_holds_its_state() -> None:
    """O16: breaks if a switch is missing from the panel or its default is not off."""
    page = html(_laid()[0])
    assert 'id="feat-body"' in page
    for name in ("Continuous zoom", "Matrix", "Signals lens", "Location fold", "Focus"):
        assert f"'{name}'" in APP_JS
    for name in ("Findings", "Changes", "Unit view", "Groups folded", "All devices", "Lanes"):
        assert f"'{name}'" in APP_JS
    assert (
        "feat: { zoom: false, matrix: false, signals: false, locfold: false, focus: false" in APP_JS
    )


def test_no_switch_says_next_round() -> None:
    """O16: breaks if a switch is still labelled as landing in a later round."""
    assert "next round" not in APP_JS


def test_continuous_zoom_is_live_and_composes_the_recorded_levels_in_the_page() -> None:
    """O6: breaks if the switch stays disabled, the script is missing, or zoom ships data."""
    page = html(_laid()[0])
    assert "['zoom', 'Continuous zoom']" in APP_JS
    assert "const zoomUpdate" in page
    assert "childViewOf" in page
    assert "zoom" not in _data()
    assert "layout" not in APP_JS.split("const zoomFit")[1].split("const zoomElements")[0]


def test_an_open_folds_data_has_member_rows_and_no_positions() -> None:
    """A15 (B2): breaks if a fold is placed open, or a member row carries a position.

    A fold's members are rows of its box, a reference and text only; no view has a fold open.
    """
    views = _data()["views"]
    assert {v["open"][0] for v in views if v["open"] is not None} <= {"item"}
    boxes = [b for v in views for b in v["boxes"] if b["ref"][0] == "fields"]
    assert boxes
    for box in boxes:
        assert f"({len(box['members'])})" in box["lines"][0]
        for member in box["members"]:
            assert set(member) == {"lines", "ref", "text"}
            assert member["ref"][0] == "item"
            assert member["lines"]


def test_a_folds_member_rows_are_one_per_member_and_name_their_line() -> None:
    """O14: breaks if a fold repeats a member row, or a field device lacks its line text."""
    for view in _data()["views"]:
        for box in view["boxes"]:
            rows = [(m["ref"][1], tuple(m["lines"])) for m in box["members"]]
            assert len(rows) == len(set(rows))
            if box["ref"][0] == "fields":
                assert all(m["text"] for m in box["members"])
    named = [m for v in _data()["views"] for b in v["boxes"] for m in b["members"] if m["text"]]
    assert len(named) > 1


def test_a_field_fold_member_row_reads_as_a_stub_label_carrier_first() -> None:
    """O14: breaks if a member row joins its text with " - " again, or drops the carrier."""
    rows = [
        m["text"]
        for v in _data()["views"]
        for b in v["boxes"]
        if b["ref"][0] == "fields"
        for m in b["members"]
    ]
    assert sorted(rows) == ["-WM1 → +FLD-M1", "-WM2 → +FLD-M2"]
