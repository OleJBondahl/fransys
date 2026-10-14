"""The overview engine on the two worked examples: every view placed, lint-clean and written.

The station and the cabinet are the block-diagram worked examples. Each test names what breaks it.
"""

from dataclasses import replace
from functools import cache
from typing import Any

import pytest
from test_block_diagram_worked_examples import _station
from test_units_worked_example import _build_cabinet_own

from fransys_layout.engines.diagram.sizes import tab_height, tab_reach
from fransys_layout.engines.overview import lay_out_overview
from fransys_layout.engines.overview.place import place_view, view_scene
from fransys_layout.engines.overview.read import read_views
from fransys_layout.engines.schematic.read.reading import profile_and_sheet
from fransys_layout.lint import lint_diagram
from fransys_layout.lint.codes import DIAGRAM_BOX_OVERLAP, DIAGRAM_LINE_THROUGH_BOX
from fransys_model.derive import (
    field_fold,
    fold_level,
    line_tabs,
    location_fold,
    overview_level,
    strip_stubs,
    strip_view,
)
from fransys_model.derive.rows import ItemKind
from fransys_model.layout import (
    AUTHORED_KINDS,
    CABLE_KINDS,
    DERIVED_KINDS,
    DIAGRAM_KINDS,
    OVERVIEW_KINDS,
    OverviewBox,
    OverviewLine,
    OverviewMode,
    OverviewRef,
    OverviewRefKind,
    OverviewView,
    layout_of,
)
from fransys_model.vocab.tables import units

NAMES = ("station", "cabinet")

# Crossings between distinct lines per (model, view index); the views are sorted by key.
# Measured with `_crossings` on the current engine. A ratchet: a rise fails, a fall is a cleanup.
_CROSSINGS = {
    ("station", 0): 0,
    ("station", 1): 0,
    ("station", 2): 0,
    ("station", 3): 0,
    ("station", 4): 0,
    ("station", 5): 0,
    ("station", 6): 0,
    ("station", 7): 0,
    ("station", 8): 0,
    ("station", 9): 0,
    ("station", 10): 0,
    ("cabinet", 0): 0,
    ("cabinet", 1): 0,
    ("cabinet", 2): 0,
    ("cabinet", 3): 0,
    ("cabinet", 4): 0,
    ("cabinet", 5): 0,
    ("cabinet", 6): 0,
    ("cabinet", 7): 0,
    ("cabinet", 8): 0,
}


@cache
def _model(name: str) -> Any:
    if name == "station":
        return _station()
    return _build_cabinet_own(prefix="p", name="C1")[0].model


@cache
def _laid(name: str) -> Any:
    return lay_out_overview(_model(name))


def _views(model: Any) -> list[Any]:
    """The written views, sorted by key so that an index is stable."""
    return sorted(layout_of(model, OverviewView).values(), key=lambda v: v.key)


def _of(model: Any, kind: type, view: Any) -> list[Any]:
    return [r for r in layout_of(model, kind).values() if r.view == view.id]  # ty: ignore[unresolved-attribute] -- `kind` is a record type with a view


def _subject(box: Any) -> Any:
    return box.ref.unit if box.ref.unit is not None else box.ref.item


def _strip_ref(strip: Any) -> OverviewRef:
    return OverviewRef(kind=OverviewRefKind.ITEM, item=strip)


_PLAIN_AND_LANES = (OverviewMode.PLAIN, OverviewMode.LANES)


def _expected_views(model: Any) -> set[tuple[Any, Any, Any, Any]]:
    """The (unit, level, mode, open) the engine must write for these group-less models.

    A non-empty level plain, then its open strips; a unit also draws lanes (O4) for the level and
    each open strip, and opens straight, strips see-through, with each strip that level holds or
    passes opened (O5).
    """
    found: set[tuple[Any, Any, Any, Any]] = set()
    for unit in (None, *units(model)):
        level = overview_level(model, unit)
        if not level.boxes:
            continue
        found.add((unit, None, OverviewMode.PLAIN, None))
        if unit is not None:
            found.add((unit, None, OverviewMode.SEE_THROUGH, None))
            found.add((unit, None, OverviewMode.LANES, None))
            opened = [
                _strip_ref(b.box)
                for b in level.boxes
                if b.kind is ItemKind.STRIP and b.terminals > 0
            ]
            found.update((unit, None, mode, ref) for ref in opened for mode in _PLAIN_AND_LANES)
            found.update(
                (unit, None, OverviewMode.SEE_THROUGH, _strip_ref(note.strip))
                for note in fold_level(model, unit, fold=False).strips
            )
    found.update(_expected_system_folds(model))
    return found


def _expected_system_folds(model: Any) -> set[tuple[Any, Any, Any, Any]]:
    """O9: the location view with two top places; the field view, never one per open box (B2)."""
    found: set[tuple[Any, Any, Any, Any]] = set()
    if location_fold(model) is not None:
        found.add((None, None, OverviewMode.LOCATION, None))
    folds = field_fold(model)
    if folds:
        found.add((None, None, OverviewMode.FIELDS, None))
    return found


def _expected_boxes(model: Any, view: Any) -> set[Any]:
    """The level's box subjects; an open strip is replaced by its terminals."""
    level = overview_level(model, view.unit)
    boxes = {b.box for b in level.boxes}
    if view.open is None:
        return boxes
    terminals = {t.item for t in strip_view(model, view.open.item, view.unit).terminals}
    return (boxes - {view.open.item}) | terminals


def _segments(line: Any) -> list[tuple[Any, Any]]:
    """The non-degenerate segments of a line, each asserted orthogonal."""
    found = []
    for p, q in zip(line.points, line.points[1:], strict=False):
        if (p.x, p.y) == (q.x, q.y):
            continue
        assert p.x == q.x or p.y == q.y, f"a diagonal segment in {line.key}"
        found.append((p, q))
    return found


def _crossings(lines: list[Any]) -> int:
    """Proper crossings of horizontal and vertical segments of two different lines.

    Shared endpoints on a box are never counted: a crossing needs both segments' interiors.
    """
    segs = [(i, p, q) for i, line in enumerate(lines) for p, q in _segments(line)]
    count = 0
    for i, p, q in segs:
        for j, r, s in segs:
            if j <= i or (p.y == q.y) == (r.y == s.y):
                continue
            (h1, h2), (v1, v2) = ((p, q), (r, s)) if p.y == q.y else ((r, s), (p, q))
            x1, x2 = sorted((h1.x, h2.x))
            y1, y2 = sorted((v1.y, v2.y))
            if x1 < v1.x < x2 and y1 < h1.y < y2:
                count += 1
    return count


@pytest.mark.parametrize("name", NAMES)
def test_every_level_and_open_strip_is_written_and_clean(name):
    """Breaks if a level or open strip is skipped, or if a view writes a finding.

    The expected views come from `overview_level` and `strip_view`, not from the engine.
    """
    model = _model(name)
    out, findings = _laid(name)
    assert findings == ()
    views = _views(out)
    assert {(v.unit, v.level, v.mode, v.open) for v in views} == _expected_views(model)
    assert len(views) == len(_expected_views(model))


@pytest.mark.parametrize("name", NAMES)
def test_each_view_has_the_level_boxes_stubs_and_lines(name):
    """Breaks if a box is missing or extra, a stub is dropped, or a line is not written.

    An unfolded level has one box per level box and per stub, and one line per line and stub.
    An open strip has its terminals in place of the strip, and no more stubs than the level.
    """
    out, _ = _laid(name)
    model = _model(name)
    for view in _views(out):
        if view.mode is not OverviewMode.PLAIN:
            continue
        level = overview_level(model, view.unit)
        boxes = _of(out, OverviewBox, view)
        subjects = {_subject(b) for b in boxes if b.stub_of is None}
        assert subjects == _expected_boxes(model, view)
        stubs = [b for b in boxes if b.stub_of is not None]
        lines = _of(out, OverviewLine, view)
        if view.open is None:
            ends = {(s.box, s.end) for s in level.stubs}
            carried = {(s.box, s.end, s.kind, s.via) for s in level.stubs}
            assert len(stubs) == len(ends)
            assert len(lines) == len(level.lines) + len(carried)
        else:
            kept = {(s.box, s.end) for s in level.stubs if s.box != view.open.item}
            held = {  # the terminals share one stub box per far end (O5)
                s.end for t in strip_stubs(model, view.open.item, view.unit) for s in t.stubs
            }
            assert len(stubs) == len(kept) + len(held)


@pytest.mark.parametrize("name", NAMES)
def test_crossings_do_not_rise_and_the_lint_holds_on_the_scenes(name):
    """Breaks if a view gains a crossing beyond the table, or a placed scene fails lint.

    The lint is run again on each placed scene, not only through the engine's findings.
    """
    out, _ = _laid(name)
    views = _views(out)
    assert {k for k in _CROSSINGS if k[0] == name} == {(name, i) for i in range(len(views))}
    for i, view in enumerate(views):
        assert _crossings(_of(out, OverviewLine, view)) <= _CROSSINGS[(name, i)]
    model = _model(name)
    for facts in read_views(model):
        sheet = place_view(facts)
        assert sheet is not None
        assert lint_diagram(view_scene(facts, sheet)) == ()


@pytest.mark.parametrize("name", NAMES)
def test_the_pass_is_idempotent_and_writes_only_overview_kinds(name):
    """Breaks if a second pass changes the model, or any kind outside OVERVIEW_KINDS changes.

    The other kinds are compared by ids, as the diagram engine's test does.
    """
    model = _model(name)
    once, _ = _laid(name)
    twice, _ = lay_out_overview(once)
    assert twice == once
    others = [*AUTHORED_KINDS, *DERIVED_KINDS, *CABLE_KINDS, *DIAGRAM_KINDS]
    others = [k for k in others if k not in OVERVIEW_KINDS]
    for kind in others:
        assert set(layout_of(once, kind)) == set(layout_of(model, kind))
    assert layout_of(once, OverviewView)


def _tab_ends(model: Any, view: Any) -> dict[tuple[Any, Any, Any], tuple[Any, Any]]:
    """The block diagram's tab texts of a level's cable lines, keyed by (a, b, cable)."""
    return {
        (t.ref.a, t.ref.b, t.ref.via): (t.tab_a, t.tab_b)
        for t in line_tabs(model, view.unit)
        if t.ref.via is not None
    }


def _on(tab: Any, box: Any, point: Any, text_height: int) -> bool:
    """Whether `point` is on `tab`, the rectangle outside the edge of `box` that it stands on."""
    reach, height = tab_reach(tab.text_width), tab_height(text_height)
    return (
        tab.x <= point.x <= tab.x + reach
        and tab.y <= point.y <= tab.y + height
        and (tab.x + reach == box.x or tab.x == box.x + box.width)
    )


@pytest.mark.parametrize("name", NAMES)
def test_cable_lines_end_on_their_tabs_at_the_box_border(name):
    """Breaks if a tab is missing or inside the box, or a line ends off the tab of its end.

    The tabs are the block diagram's `line_tabs`; each cable line with a tab text ends, at that
    end, on a tab outside the border of its box. A box has one tab per tab end.
    """
    out, _ = _laid(name)
    model = _model(name)
    text_height = profile_and_sheet(model)[0].text_height
    checked = 0
    for view in _views(out):
        if view.mode is not OverviewMode.PLAIN or view.open is not None:
            continue
        ends = _tab_ends(model, view)
        boxes = {b.id: b for b in _of(out, OverviewBox, view)}
        wanted: dict[Any, int] = {}
        for line in _of(out, OverviewLine, view):
            a, b = boxes[line.a], boxes[line.b]
            texts = ends.get((_subject(a), _subject(b), line.via))
            if texts is None or line.kind != "cable":
                continue
            for text, box, point in zip(
                texts, (a, b), (line.points[0], line.points[-1]), strict=True
            ):
                if text is None:
                    continue
                wanted[box.id] = wanted.get(box.id, 0) + 1
                assert any(_on(t, box, point, text_height) for t in box.tabs)
                checked += 1
        for box in boxes.values():
            assert len(box.tabs) == wanted.get(box.id, 0)
    assert (checked > 0) == (name == "station")  # the cabinet's lines carry no tab text


def _codes(facts: Any, sheet: Any) -> set[str]:
    return {f.code for f in lint_diagram(view_scene(facts, sheet))}


def _first_view_with_three_boxes(model: Any) -> tuple[Any, Any]:
    for facts in read_views(model):
        if len(facts.boxes) >= 3:
            sheet = place_view(facts)
            assert sheet is not None
            return facts, sheet
    pytest.fail("no view with three boxes")


def test_a_box_on_another_box_trips_the_overlap_check():
    """Breaks if the overlap check stops seeing two boxes at one place in a placed view."""
    facts, sheet = _first_view_with_three_boxes(_model("station"))
    one, two, *_ = sheet.boxes
    moved = replace(two, x=one.x, y=one.y)
    boxes = tuple(moved if b is two else b for b in sheet.boxes)
    assert DIAGRAM_BOX_OVERLAP in _codes(facts, replace(sheet, boxes=boxes))


def test_a_box_on_a_foreign_line_trips_the_line_through_box_check():
    """Breaks if the through-box check stops seeing a box centred on a line's middle.

    The box is one that is not an end of the line. The first such pair in sheet order is used.
    """
    facts, sheet = _first_view_with_three_boxes(_model("station"))
    for line in sheet.lines:
        ends = {line.a, line.b}
        for p, q in zip(line.points, line.points[1:], strict=False):
            if (p.x, p.y) == (q.x, q.y):
                continue
            mx, my = (p.x + q.x) // 2, (p.y + q.y) // 2
            for box in sheet.boxes:
                if box.box in ends:
                    continue
                moved = replace(box, x=mx - box.width // 2, y=my - box.height // 2)
                boxes = tuple(moved if b is box else b for b in sheet.boxes)
                if DIAGRAM_LINE_THROUGH_BOX in _codes(facts, replace(sheet, boxes=boxes)):
                    return
    pytest.fail("no box could be put on a foreign line's middle to trip the check")
