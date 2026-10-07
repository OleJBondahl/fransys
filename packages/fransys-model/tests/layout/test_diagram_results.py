"""BD-M4: the block diagram's layout records and its A2 sheet (decision model-0167, spec BD6)."""

import dataclasses
from decimal import Decimal
from typing import Any

import pytest
from layout_examples import PRODUCED_BY, drawn_function, sheet_format

from fransys_model.kernel import Draft, Id, Model, Origin, SchemaError, dumps, freeze, loads
from fransys_model.layout import (
    CABLE_KINDS,
    DERIVED_KINDS,
    DIAGRAM_KINDS,
    BoxRef,
    DiagramBox,
    DiagramLine,
    DiagramMarker,
    DiagramSheet,
    Profile,
    RoutePoint,
    Side,
    TabCell,
    a2_sheet_format,
    default_sheet_format,
    derived_layout_ids,
    layout_of,
    sheet_for,
)
from fransys_model.vocab.enums import PageKind
lazy from fransys_model.vocab.core import Unit

_ORIGIN = Origin(file="test_diagram_results.py", line=1, note="fixture")
_UNIT: Id[Unit] = Id(kind="unit", value="9" * 32)
_KEY = ("layout", "diagram-engine", "sheet", "1")


def _sheet() -> DiagramSheet:
    return DiagramSheet(
        id=Id(kind="layout.diagram_sheet", value="a" * 32),
        key=_KEY,
        unit=None,
        number=1,
        produced_by=PRODUCED_BY,
    )


_TABS = (
    TabCell(index=0, line=drawn_function()[0].id, side=Side.E, y=8, text_width=12),
    TabCell(index=1, line=None, side=Side.W, y=16, text_width=6),
)


def _box(**changes: Any) -> DiagramBox:
    fields: dict[str, Any] = {
        "id": Id(kind="layout.diagram_box", value="b" * 32),
        "key": (*_KEY, "box"),
        "sheet": _sheet().id,
        "subject": BoxRef(unit=None, item=drawn_function()[0].id),
        "dashed": False,
        "x": 8,
        "y": 8,
        "width": 40,
        "height": 24,
        "tabs": _TABS,
        "produced_by": PRODUCED_BY,
    }
    return DiagramBox(**{**fields, **changes})


_POINTS = (RoutePoint(index=0, x=48, y=16), RoutePoint(index=1, x=96, y=16))


def _line(points: tuple[RoutePoint, ...] = _POINTS) -> DiagramLine:
    return DiagramLine(
        id=Id(kind="layout.diagram_line", value="c" * 32),
        key=(*_KEY, "line"),
        sheet=_sheet().id,
        cable=drawn_function()[0].id,
        a=_box().subject,
        b=_box().subject,
        points=points,
        text_x=72,
        text_y=12,
        produced_by=PRODUCED_BY,
    )


def _marker() -> DiagramMarker:
    return DiagramMarker(
        id=Id(kind="layout.diagram_marker", value="d" * 32),
        key=(*_KEY, "marker"),
        sheet=_sheet().id,
        line=_line().id,
        at_sheet=2,
        x=96,
        y=16,
        produced_by=PRODUCED_BY,
    )


def _freeze(*records: Any) -> Model:
    draft = Draft()
    draft.extend(records, origin=_ORIGIN)
    return freeze(draft)


def _model() -> Model:
    return _freeze(drawn_function()[0], drawn_function()[1], _sheet(), _box(), _line(), _marker())


def test_diagram_records_freeze_and_round_trip() -> None:
    """All four kinds freeze, read back through `layout_of` and survive dumps and loads."""
    model = _model()
    assert loads(dumps(model)) == model
    assert layout_of(model, DiagramSheet)[_sheet().id].number == 1
    assert layout_of(model, DiagramBox)[_box().id].tabs == _TABS
    assert layout_of(model, DiagramLine)[_line().id].points == _POINTS
    assert layout_of(model, DiagramMarker)[_marker().id].at_sheet == 2


def test_a_box_may_hold_a_unit_instead_of_an_item() -> None:
    """A box is a unit instance or an item."""
    assert _box(subject=BoxRef(unit=_UNIT, item=None)).subject.unit == _UNIT


@pytest.mark.parametrize(
    ("unit", "item"), [(_UNIT, drawn_function()[0].id), (None, None)], ids=["both", "neither"]
)
def test_a_box_ref_holds_exactly_one_of_unit_and_item(unit: Any, item: Any) -> None:
    """Both set and neither set are refused."""
    with pytest.raises(SchemaError):
        BoxRef(unit=unit, item=item)


def test_tabs_are_stored_in_index_order() -> None:
    """`DiagramBox.tabs` is sorted by `index`, whatever order it was built in."""
    assert _box(tabs=tuple(reversed(_TABS))).tabs == _TABS


def test_a_tab_index_may_not_repeat() -> None:
    """Two tabs with one `index` have no order."""
    with pytest.raises(SchemaError):
        _box(tabs=(_TABS[0], dataclasses.replace(_TABS[1], index=0)))


def test_line_points_are_stored_in_index_order() -> None:
    """`DiagramLine.points` is sorted by `index`."""
    assert _line(tuple(reversed(_POINTS))).points == _POINTS


def test_a_line_point_index_may_not_repeat() -> None:
    """Two vertices with one `index` have no order."""
    with pytest.raises(SchemaError):
        _line((_POINTS[0], RoutePoint(index=0, x=1, y=1)))


def test_the_diagram_kinds_are_the_four_records_and_no_other_tuple_holds_them() -> None:
    """`DIAGRAM_KINDS` is the four classes; the cable and schematic tuples hold none."""
    assert set(DIAGRAM_KINDS) == {DiagramSheet, DiagramBox, DiagramLine, DiagramMarker}
    assert not set(DIAGRAM_KINDS) & {*CABLE_KINDS, *DERIVED_KINDS}


def test_the_diagram_pass_names_only_its_own_ids() -> None:
    """`derived_layout_ids(model, DIAGRAM_KINDS)` is the four records; the default none."""
    model = _model()
    assert set(derived_layout_ids(model, DIAGRAM_KINDS)) == {
        _sheet().id,
        _box().id,
        _line().id,
        _marker().id,
    }
    assert derived_layout_ids(model) == ()
    assert derived_layout_ids(model, CABLE_KINDS) == ()


def test_the_block_diagram_sheet_is_the_house_a2() -> None:
    """594 x 420 mm, content 584 x 390 at (5, 5), 12 x 8 frame, whatever the profile says."""
    sheet = sheet_for(_freeze(), PageKind.BLOCK_DIAGRAM)
    assert sheet == a2_sheet_format()
    assert (sheet.width_mm, sheet.height_mm) == (594, 420)
    assert (sheet.content_x_mm, sheet.content_y_mm) == (5, 5)
    assert (sheet.content_width_mm, sheet.content_height_mm) == (584, 390)
    assert (sheet.frame_columns, sheet.frame_rows) == (12, 8)
    assert sheet.module_mm == Decimal("2.5")
    authored = sheet_format()
    profile = Profile(
        id=Id(kind="layout.profile", value="8" * 32), key=("p",), sheet_format=authored.id
    )
    assert sheet_for(_freeze(authored, profile), PageKind.BLOCK_DIAGRAM) == a2_sheet_format()


def test_every_other_page_kind_keeps_the_profile_sheet() -> None:
    """No profile gives the house A3; a profile naming a sheet gives that sheet."""
    assert sheet_for(_freeze(), PageKind.SCHEMATIC) == default_sheet_format()
    authored = sheet_format()
    profile = Profile(
        id=Id(kind="layout.profile", value="8" * 32), key=("p",), sheet_format=authored.id
    )
    model = _freeze(authored, profile)
    for kind in PageKind:
        if kind is not PageKind.BLOCK_DIAGRAM:
            assert sheet_for(model, kind) == authored, kind
