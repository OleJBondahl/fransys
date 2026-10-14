"""The overview levels on the units worked example (OVERVIEW A1, A3; model-0197).

The system level is the block diagram's rows, and no designation inside an opened unit carries
that unit's own tag.
"""

import sys
from pathlib import Path
from typing import Any

import fransys as fr
import fransys_parts
import pytest
from _model_build_cover import system_document

# `--import-mode=importlib` (root pyproject.toml) never puts `tests/` on `sys.path`.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_units_worked_example import _system_design

from fransys_model.derive import (
    field_devices,
    field_fold,
    line_tabs,
    location_fold,
    overview_level,
    overview_line_text,
)
from fransys_model.derive.block_diagram import box_lines, diagram_lines
from fransys_model.derive.instance_tag import unit_tag
from fransys_model.vocab.tables import units


@pytest.fixture(scope="module")
def model():
    parts = fransys_parts.load("demo_parts")
    design, _field1, _field2 = _system_design(parts)
    return fr.build(parts, design.draft(), system_document()).model


def test_the_system_level_is_the_block_diagram_rows(model) -> None:
    """Boxes and lines, compared as printed text, equal `diagram_lines` and `box_lines`."""
    level = overview_level(model, None)
    rows = diagram_lines(model, None)
    assert sorted(line.label for line in level.lines) == sorted(row.designation for row in rows)
    reached = {box for row in rows for box in (row.a, row.b)}
    assert {b.box for b in level.boxes} == reached
    assert {b.lines for b in level.boxes} == {box_lines(model, box, None) for box in reached}


def test_no_designation_inside_an_opened_unit_starts_with_that_units_tag(model) -> None:
    """A unit level prints designations relative to the unit: `-X2`, never `-C1-X2`."""
    checked = 0
    for unit in units(model):
        tag = unit_tag(model, unit)
        level = overview_level(model, unit)
        texts = [
            *(t for b in level.boxes for t in (*b.lines, *b.tabs)),
            *(s.far for s in level.stubs),
            *(line.label for line in level.lines),
        ]
        checked += len(texts)
        assert not [t for t in texts if tag and t.startswith(f"-{tag}-")]
    assert checked


def test_each_cable_line_ends_on_the_tab_the_block_diagram_draws(model) -> None:
    """A12-style tab check: every system line has its `LineTab`, and each tab is on its box."""
    level = overview_level(model, None)
    rows: dict[tuple[Any, ...], Any] = {
        (row.a, row.b, row.cable): row for row in diagram_lines(model, None)
    }
    tabs = line_tabs(model, None)
    boxes = {b.box: b for b in level.boxes}
    assert {line.ref for line in level.lines} == {t.ref for t in tabs}
    named = 0
    for tab in tabs:
        row = rows[(tab.ref.a, tab.ref.b, tab.ref.via)]
        assert (tab.tab_a, tab.tab_b) == (row.tab_a, row.tab_b)
        for box, text in ((tab.ref.a, tab.tab_a), (tab.ref.b, tab.tab_b)):
            if text is not None:
                named += 1
                assert text in boxes[box].tabs
    assert named


def test_the_location_fold_puts_each_system_box_in_one_top_place(model) -> None:
    """O9 on the units example: every box lands once; a line counts the cables between places."""
    fold = location_fold(model)
    assert fold is not None
    level = overview_level(model, None)
    placed = [box for held in fold.boxes for box in held.boxes]
    assert sorted(placed) == sorted(b.box for b in level.boxes)
    assert len(fold.boxes) >= 2
    system_cables = {line.ref.via for line in level.lines}
    crossing = {cable for line in fold.lines for cable in line.cables}
    assert crossing
    assert crossing <= system_cables
    assert all(line.count == len(line.cables) for line in fold.lines)


def test_a_field_device_is_an_item_whose_every_connection_lands_in_one_unit(model) -> None:
    """O9: M1 and M2 each belong to one cabinet; K1, wired to both cabinets, belongs to none."""
    level = overview_level(model, None)
    name = {b.box: b.lines[0] for b in level.boxes}
    owner = {name[item]: unit for item, unit in field_devices(model).items()}
    assert set(owner) == {"+FLD-M1", "+FLD-M2"}
    assert owner["+FLD-M1"] != owner["+FLD-M2"]
    assert "+FLD-K1" in name.values()
    folds = field_fold(model)
    assert [f.lines for f in folds] == [("Field devices (1)",)] * 2
    assert {name[d] for f in folds for d in f.devices} == {"+FLD-M1", "+FLD-M2"}
    assert all(f.cables for f in folds)


def test_the_system_lines_print_the_block_diagrams_designations(model) -> None:
    """A1: the plain system level prints the block diagram's own line text."""
    level = overview_level(model, None)
    printed = sorted(overview_line_text(line) for line in level.lines)
    assert printed == sorted(row.designation for row in diagram_lines(model, None))
    assert any(printed)
