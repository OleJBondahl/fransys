"""The placed overview rows equal the `layout.overview_*` records they come from (model-0306).

Each test names what breaks it. The model is the units worked example, laid out by the engine.
"""

import sys
from functools import cache
from pathlib import Path
from typing import Any

import fransys as fr
import fransys_parts
from _model_build_cover import system_document

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_units_worked_example import _system_design

from fransys_layout.engines.overview import lay_out_overview
from fransys_model.derive import overview_placed_views
from fransys_model.kernel import make_id
from fransys_model.layout import (
    OverviewBox,
    OverviewLine,
    OverviewMode,
    OverviewView,
    box_key,
    layout_of,
    line_key,
    view_key,
)


@cache
def _model() -> Any:
    parts = fransys_parts.load("demo_parts")
    design, _field1, _field2 = _system_design(parts)
    return lay_out_overview(fr.build(parts, design.draft(), system_document()).model)[0]


def _modes() -> set[OverviewMode]:
    return {p.rows.mode for p in overview_placed_views(_model())}


def test_the_example_has_a_lanes_view_and_a_strips_view() -> None:
    """The comparison below must cover a lanes view and a view that opens a strip."""
    placed = overview_placed_views(_model())
    assert OverviewMode.LANES in _modes()
    assert any(p.rows.open is not None for p in placed)


def test_every_placed_box_and_line_equals_its_record() -> None:
    """A placed box or line differs in a number or an order from the record it came from."""
    model = _model()
    boxes, lines = layout_of(model, OverviewBox), layout_of(model, OverviewLine)
    placed = overview_placed_views(model)
    assert placed
    for view in placed:
        rows = view.rows
        key = view_key(rows.unit, rows.level, rows.mode, rows.open)
        assert len(view.boxes) == len(rows.boxes)
        for row, got in zip(rows.boxes, view.boxes, strict=True):
            rec = boxes[make_id(OverviewBox, box_key(key, row.key))]
            assert (got.x, got.y, got.width, got.height) == (rec.x, rec.y, rec.width, rec.height)
            assert [(t.index, t.x, t.y, t.text_width, t.width, t.height) for t in got.tabs] == [
                (t.index, t.x, t.y, t.text_width, t.width, t.height) for t in rec.tabs
            ]
            assert (got.ref.kind, got.ref.unit, got.ref.item, got.ref.node) == (
                row.key.ref.kind,
                row.key.ref.unit,
                row.key.ref.item,
                row.key.ref.node,
            )
        index = {b.key: i for i, b in enumerate(rows.boxes)}
        for row, got in zip(rows.lines, view.lines, strict=True):
            ends = (row.a, row.b), (row.via, row.strip)
            rec = lines[make_id(OverviewLine, line_key(key, row.kind, *ends))]
            assert (got.a, got.b) == (index[row.a], index[row.b])
            assert [(p.x, p.y) for p in got.points] == [(p.x, p.y) for p in rec.points]
            assert (got.text_x, got.text_y) == (rec.text_x, rec.text_y)


def test_the_lane_heads_are_the_views_stored_triples() -> None:
    """A lanes view's heads differ from `ext["lane_heads"]`."""
    model = _model()
    views = layout_of(model, OverviewView)
    lanes = [p for p in overview_placed_views(model) if p.rows.mode is OverviewMode.LANES]
    assert any(p.lane_heads for p in lanes)
    for view in lanes:
        rows = view.rows
        rec = views[make_id(OverviewView, view_key(rows.unit, rows.level, rows.mode, rows.open))]
        assert [(h.node, h.x, h.y) for h in view.lane_heads] == list(rec.ext.get("lane_heads", ()))  # ty: ignore[invalid-argument-type] -- ext values are a Value union


def test_an_unplaced_model_has_no_placed_view() -> None:
    """A model the engine never laid out yields placed views anyway."""
    parts = fransys_parts.load("demo_parts")
    design, _field1, _field2 = _system_design(parts)
    assert overview_placed_views(fr.build(parts, design.draft(), system_document()).model) == ()
