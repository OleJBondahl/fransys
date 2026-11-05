"""The diagram engine's glue: the pass, the lint scene feed and the cut acceptance."""

from dataclasses import replace
from functools import cache
from typing import Any

import pytest
from diagram_models import chain, fanout, loose, one_box, station

from electrical_symbols import LIBRARY
from fransys_layout import lay_out_diagrams
from fransys_layout.engines.diagram.read import read_diagrams
from fransys_layout.engines.overview.compose import place_diagram
from fransys_layout.engines.overview.scene import scene_of
from fransys_layout.geometry import WIRING_GRID, Point
from fransys_layout.lint import lint_diagram
from fransys_layout.lint.codes import (
    DIAGRAM_BOX_OVERLAP,
    DIAGRAM_LINE_OFF_BOX,
    DIAGRAM_LINE_THROUGH_BOX,
    DIAGRAM_TEXT_OVERLAP,
)
from fransys_model.kernel import Severity


@cache
def _station():
    (facts,) = read_diagrams(station(), LIBRARY)
    placed = place_diagram(facts)
    assert placed is not None
    return facts, placed.sheets[0]


def _codes(facts, sheet):
    return {f.code for f in lint_diagram(scene_of(facts, sheet))}


def test_the_station_pass_has_no_error_and_places_a_diagram():
    layout, findings = lay_out_diagrams(station(), LIBRARY)
    assert not [f for f in findings if f.severity is Severity.ERROR]
    assert len(layout.diagrams) >= 1
    assert layout.sheet_places()


def test_the_pass_is_deterministic():
    assert lay_out_diagrams(station(), LIBRARY) == lay_out_diagrams(station(), LIBRARY)


def test_clean_sheets_lint_clean():
    facts, sheet = _station()
    assert _codes(facts, sheet) == set()
    for n in (3, _first_cut()):
        (cf,) = read_diagrams(chain(n), LIBRARY)
        placed = place_diagram(cf)
        assert placed is not None
        assert [_codes(cf, s) for s in placed.sheets] == [set()] * len(placed.sheets)


def test_two_overlapping_boxes_trip_the_overlap_check():
    facts, sheet = _station()
    one, two, *rest = sheet.boxes
    moved = replace(two, x=one.x, y=one.y)
    assert DIAGRAM_BOX_OVERLAP in _codes(facts, replace(sheet, boxes=(one, moved, *rest)))


def test_a_third_box_on_a_line_trips_the_line_through_box_check():
    facts, sheet = _station()
    line = sheet.lines[0]
    ends = {line.a, line.b}
    mid = next(b for b in sheet.boxes if b.box not in ends)
    p, q = next((p, q) for p, q in zip(line.points, line.points[1:], strict=False) if p != q)
    moved = replace(mid, x=(p.x + q.x) // 2 - mid.width // 2, y=(p.y + q.y) // 2 - mid.height // 2)
    boxes = tuple(moved if b is mid else b for b in sheet.boxes)
    assert DIAGRAM_LINE_THROUGH_BOX in _codes(facts, replace(sheet, boxes=boxes))


def test_two_labels_on_one_spot_trip_the_text_overlap_check():
    facts, sheet = _station()
    one, two, *rest = sheet.lines
    moved = replace(two, text_x=one.text_x, text_y=one.text_y)
    assert DIAGRAM_TEXT_OVERLAP in _codes(facts, replace(sheet, lines=(one, moved, *rest)))


def test_a_label_on_a_box_trips_the_text_overlap_check():
    facts, sheet = _station()
    line, box = sheet.lines[0], sheet.boxes[0]
    moved = replace(line, text_x=box.x + box.width // 2, text_y=box.y + box.height // 2)
    assert DIAGRAM_TEXT_OVERLAP in _codes(facts, replace(sheet, lines=(moved, *sheet.lines[1:])))


def test_a_line_ending_short_of_its_box_trips_the_off_box_check():
    facts, sheet = _station()
    line = sheet.lines[0]
    p, q = line.points[-2:]
    step = WIRING_GRID if (q.x > p.x or q.y > p.y) else -WIRING_GRID
    end = Point(x=q.x - step, y=q.y) if p.y == q.y else Point(x=q.x, y=q.y - step)
    moved = replace(line, points=(*line.points[:-1], end))
    assert DIAGRAM_LINE_OFF_BOX in _codes(facts, replace(sheet, lines=(moved, *sheet.lines[1:])))


@cache
def _first_cut() -> int:
    """The smallest chain length whose A2 diagram needs more than one sheet."""
    for n in range(2, 41):
        (facts,) = read_diagrams(chain(n), LIBRARY)
        placed = place_diagram(facts)
        if placed is not None and len(placed.sheets) > 1:
            return n
    pytest.fail("no chain of up to 40 boxes needs a second sheet")


@cache
def _cut_layout():
    return lay_out_diagrams(chain(_first_cut()), LIBRARY)[0]


def test_a_long_chain_is_cut_into_numbered_sheets():
    layout, findings = lay_out_diagrams(chain(_first_cut()), LIBRARY)
    assert not [f for f in findings if f.severity is Severity.ERROR]
    numbers = [n for _, n in layout.sheet_places()]
    assert numbers == list(range(1, len(numbers) + 1))
    assert len(numbers) > 1


def test_each_cut_line_has_a_marker_on_both_sheets():
    by_line: dict[Any, Any] = {}
    for diagram in _cut_layout().diagrams:
        for sheet in diagram.sheets:
            for marker in sheet.markers:
                by_line.setdefault((marker.cable, marker.a, marker.b), []).append((sheet.number, marker.at_sheet))
    assert by_line
    for pairs in by_line.values():
        assert len(pairs) == 2
        (n1, at1), (n2, at2) = sorted(pairs)
        assert (at1, at2) == (n2, n1)
        assert n1 != n2


def test_the_cut_falls_between_columns():
    facts, placed = _cut_facts()
    first, second = placed.sheets[0], placed.sheets[1]
    left = max(b.x + b.width for b in first.boxes)
    assert left <= facts.width
    assert min(b.x for b in second.boxes) >= 0


@cache
def _cut_facts():
    (facts,) = read_diagrams(chain(_first_cut()), LIBRARY)
    placed = place_diagram(facts)
    assert placed is not None
    return facts, placed


@pytest.mark.parametrize(
    ("model", "code"),
    [
        (one_box, "DIAGRAM_CABLE_ONE_BOX"),
        (fanout, "DIAGRAM_CABLE_FANOUT"),
        (loose, "DIAGRAM_LOOSE_WIRE"),
    ],
)
def test_the_read_findings_come_through(model, code):
    assert code in {f.code for f in lay_out_diagrams(model(), LIBRARY)[1]}
    assert code not in {f.code for f in lay_out_diagrams(station(), LIBRARY)[1]}
