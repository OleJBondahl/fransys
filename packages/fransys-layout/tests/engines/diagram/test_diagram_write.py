"""The diagram engine's writer: placed diagrams to derived `layout.diagram_*` records (BD8)."""

from functools import cache

import pytest
from diagram_models import station

from fransys_layout import lay_out_cables
from fransys_layout.engines.diagram.read import read_diagrams
from fransys_layout.engines.diagram.values import (
    PlacedBox,
    PlacedDiagram,
    PlacedLine,
    PlacedMarker,
    PlacedSheet,
    PlacedTab,
)
from fransys_layout.engines.diagram.write import write_diagrams
from fransys_layout.geometry import Facing, LayoutError, Point
from fransys_model.kernel import make_id, render_id
from fransys_model.layout import (
    CABLE_KINDS,
    DIAGRAM_KINDS,
    CableBlock,
    DiagramBox,
    DiagramLine,
    DiagramMarker,
    DiagramSheet,
    Side,
    layout_of,
)


@cache
def _base():
    """The station with its cable blocks written, so the diagram pass has others to leave."""
    return lay_out_cables(station())[0]


@cache
def _facts():
    (facts,) = read_diagrams(station())
    unit_box = next(b.box for b in facts.boxes if b.box.kind == "unit")
    item_box = next(b.box for b in facts.boxes if b.box.kind == "item")
    return facts, unit_box, item_box


def _line(cable, a, b, y=0):
    return PlacedLine(
        cable=cable,
        a=a,
        b=b,
        points=(Point(x=8, y=y), Point(x=16, y=y), Point(x=16, y=y + 8)),
        text_x=8,
        text_y=y,
    )


def _marker(cable, a, b, at_sheet, x):
    return PlacedMarker(cable=cable, a=a, b=b, at_sheet=at_sheet, x=x, y=8)


def _sheet(number=1, *, lines=(), markers=(), boxes=()):
    return PlacedSheet(
        number=number, boxes=tuple(boxes), lines=tuple(lines), markers=tuple(markers)
    )


def _diagram(*sheets, unit=None):
    return PlacedDiagram(unit=unit, sheets=tuple(sheets))


def _first():
    facts, unit_box, item_box = _facts()
    cable = facts.lines[0].cable
    tabs = (
        PlacedTab(cable=cable, side=Facing.E, y=16, text_width=40),
        PlacedTab(cable=cable, side=Facing.W, y=24, text_width=32),
    )
    boxes = (
        PlacedBox(box=unit_box, dashed=False, x=0, y=0, width=80, height=48, tabs=tabs),
        PlacedBox(box=item_box, dashed=True, x=160, y=0, width=80, height=48, tabs=()),
    )
    line = _line(cable, unit_box, item_box)
    return _diagram(_sheet(boxes=boxes, lines=(line,))), cable, unit_box, item_box


def _ids(model, kinds):
    return {i for kind in kinds for i in layout_of(model, kind)}


def test_records_carry_the_keys_ids_and_fields_of_the_placement():
    diagram, cable, unit_box, item_box = _first()
    model = write_diagrams(_base(), (diagram,))
    skey = ("layout", "diagram", "sheet", "1")
    (sheet,) = layout_of(model, DiagramSheet).values()
    assert (sheet.id, sheet.key, sheet.unit, sheet.number) == (
        make_id(DiagramSheet, skey),
        skey,
        None,
        1,
    )
    assert sheet.produced_by.startswith("fransys-layout/diagram ")
    boxes = layout_of(model, DiagramBox)
    unit_rec = boxes[make_id(DiagramBox, (*skey, "box", render_id(unit_box)))]
    assert (unit_rec.sheet, unit_rec.dashed, unit_rec.width, unit_rec.height) == (
        sheet.id,
        False,
        80,
        48,
    )
    assert layout_of(model, DiagramBox)[
        make_id(DiagramBox, (*skey, "box", render_id(item_box)))
    ].dashed
    lkey = (*skey, "line", render_id(cable), render_id(unit_box), render_id(item_box))
    line = layout_of(model, DiagramLine)[make_id(DiagramLine, lkey)]
    assert [(p.index, p.x, p.y) for p in line.points] == [(0, 8, 0), (1, 16, 0), (2, 16, 8)]
    assert (line.cable, line.sheet, line.text_x, line.text_y) == (cable, sheet.id, 8, 0)


def test_a_box_subject_is_a_unit_for_a_unit_box_and_an_item_otherwise():
    diagram, _cable, unit_box, item_box = _first()
    model = write_diagrams(_base(), (diagram,))
    subjects = {
        b.subject.unit or b.subject.item: b.subject for b in layout_of(model, DiagramBox).values()
    }
    assert (subjects[unit_box].unit, subjects[unit_box].item) == (unit_box, None)
    assert (subjects[item_box].unit, subjects[item_box].item) == (None, item_box)
    (line,) = layout_of(model, DiagramLine).values()
    assert line.a.unit == unit_box
    assert line.b.item == item_box


def test_tabs_keep_their_order_and_a_facing_maps_to_the_side_of_the_same_name():
    diagram, cable, unit_box, _ = _first()
    model = write_diagrams(_base(), (diagram,))
    unit_rec = next(b for b in layout_of(model, DiagramBox).values() if b.subject.unit == unit_box)
    assert [(t.index, t.line, t.side, t.y, t.text_width) for t in unit_rec.tabs] == [
        (0, cable, Side.E, 16, 40),
        (1, cable, Side.W, 24, 32),
    ]
    sides = {f.name: Side[f.name] for f in Facing}
    assert sides == {"N": Side.N, "E": Side.E, "S": Side.S, "W": Side.W}


def test_the_unit_reading_puts_the_unit_in_the_sheet_key_and_record():
    _read, unit_box, _item = _facts()
    model = write_diagrams(_base(), (_diagram(_sheet(), unit=unit_box),))
    (sheet,) = layout_of(model, DiagramSheet).values()
    assert sheet.unit == unit_box
    assert sheet.key == ("layout", "diagram", "sheet", "unit", render_id(unit_box), "1")


def test_a_second_call_replaces_the_first_and_leaves_the_other_kinds_alone():
    diagram, *_ = _first()
    base = _base()
    assert _ids(base, CABLE_KINDS)
    first = write_diagrams(base, (diagram,))
    second = write_diagrams(first, (_diagram(_sheet(number=2)),))
    assert [s.number for s in layout_of(second, DiagramSheet).values()] == [2]
    assert not layout_of(second, DiagramBox)
    assert not layout_of(second, DiagramLine)
    assert _ids(second, CABLE_KINDS) == _ids(base, CABLE_KINDS)
    assert layout_of(second, CableBlock) == layout_of(base, CableBlock)


def test_writing_nothing_removes_every_diagram_record():
    diagram, *_ = _first()
    cleared = write_diagrams(write_diagrams(_base(), (diagram,)), ())
    assert not _ids(cleared, DIAGRAM_KINDS)


def test_two_sheets_give_two_sheet_records():
    model = write_diagrams(_base(), (_diagram(_sheet(1), _sheet(2)),))
    assert sorted(s.number for s in layout_of(model, DiagramSheet).values()) == [1, 2]


def test_a_cut_line_is_one_line_record_per_sheet_and_each_marker_names_its_own():
    facts, unit_box, item_box = _facts()
    cable = facts.lines[0].cable
    one, two = (_sheet(n, lines=(_line(cable, unit_box, item_box),)) for n in (1, 2))
    one = _sheet(1, lines=one.lines, markers=(_marker(cable, unit_box, item_box, 2, 24),))
    two = _sheet(2, lines=two.lines, markers=(_marker(cable, unit_box, item_box, 1, 0),))
    model = write_diagrams(_base(), (_diagram(one, two),))
    lines = layout_of(model, DiagramLine)
    assert len(lines) == 2
    assert len({line.sheet for line in lines.values()}) == 2
    markers = layout_of(model, DiagramMarker).values()
    assert len(markers) == 2
    for marker in markers:
        assert lines[marker.line].sheet == marker.sheet
    by_sheet = {m.sheet: m.at_sheet for m in markers}
    sheets = {s.id: s.number for s in layout_of(model, DiagramSheet).values()}
    assert {sheets[s]: at for s, at in by_sheet.items()} == {1: 2, 2: 1}


def test_writing_twice_equals_writing_once():
    diagram, *_ = _first()
    once = write_diagrams(_base(), (diagram,))
    assert write_diagrams(once, (diagram,)) == once


def test_a_marker_with_no_line_of_its_identity_on_its_sheet_is_refused():
    facts, unit_box, item_box = _facts()
    cable = facts.lines[0].cable
    marker = _marker(cable, unit_box, item_box, 2, 24)
    with pytest.raises(LayoutError):
        write_diagrams(_base(), (_diagram(_sheet(markers=(marker,))),))
    other = _line(cable, item_box, unit_box)  # same cable, ends swapped: a different identity
    with pytest.raises(LayoutError):
        write_diagrams(_base(), (_diagram(_sheet(lines=(other,), markers=(marker,))),))
