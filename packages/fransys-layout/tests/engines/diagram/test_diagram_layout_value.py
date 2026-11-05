"""DiagramLayout: every marker has a line of its cable and ends, and sheets list in order."""

from typing import Any

import pytest

from fransys_layout import (
    DiagramLayout,
    DiagramLine,
    PlacedDiagram,
    PlacedMarker,
    PlacedSheet,
)
from fransys_layout.geometry import LayoutError, Point
from fransys_model.kernel import Id


def _id(name: str) -> Id[Any]:
    return Id(kind="item", value=name)


def _line() -> DiagramLine:
    points = (Point(x=0, y=0), Point(x=16, y=0))
    return DiagramLine(cable=_id("w"), a=_id("a"), b=_id("b"), points=points, text_x=0, text_y=0)


def _marker(b: str = "b") -> PlacedMarker:
    return PlacedMarker(cable=_id("w"), a=_id("a"), b=_id(b), at_sheet=2, x=16, y=0)


def _sheet(number: int, lines=(), markers=()) -> PlacedSheet:
    return PlacedSheet(number=number, boxes=(), lines=tuple(lines), markers=tuple(markers))


def test_a_marker_without_a_line_of_its_cable_and_ends_is_refused():
    """Breaks if the check is gone or compares only the cable."""
    sheet = _sheet(1, lines=[_line()], markers=[_marker("other")])
    with pytest.raises(LayoutError):
        DiagramLayout(diagrams=(PlacedDiagram(unit=None, sheets=(sheet,)),))


def test_a_marker_on_a_sheet_without_any_line_is_refused():
    sheet = _sheet(1, markers=[_marker()])
    with pytest.raises(LayoutError):
        DiagramLayout(diagrams=(PlacedDiagram(unit=None, sheets=(sheet,)),))


def test_a_marker_with_its_line_on_the_sheet_is_accepted():
    sheet = _sheet(1, lines=[_line()], markers=[_marker()])
    layout = DiagramLayout(diagrams=(PlacedDiagram(unit=None, sheets=(sheet,)),))
    assert layout.diagrams[0].sheets[0].markers == (_marker(),)


def test_sheet_places_are_unit_and_number_in_engine_order():
    first = PlacedDiagram(unit=_id("u2"), sheets=(_sheet(1), _sheet(2)))
    second = PlacedDiagram(unit=None, sheets=(_sheet(1),))
    layout = DiagramLayout(diagrams=(first, second))
    assert layout.sheet_places() == ((_id("u2"), 1), (_id("u2"), 2), (None, 1))


def test_an_empty_layout_has_no_sheet_places():
    assert DiagramLayout(diagrams=()).sheet_places() == ()
