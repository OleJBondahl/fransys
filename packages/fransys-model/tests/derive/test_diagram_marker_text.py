"""`diagram_marker_text`: a cut marker prints its partner's place on the other sheet (BD5, BD7)."""

from typing import Any

from fransys_model.derive.block_diagram import diagram_marker_text
from fransys_model.kernel import Draft, Id, Model, Origin, freeze, make_id
from fransys_model.layout import (
    BoxRef,
    DiagramLine,
    DiagramMarker,
    DiagramSheet,
    RoutePoint,
    layout_of,
)
from fransys_model.vocab.core import Item, Unit, UnitRelease

_ORIGIN = Origin(file="test_diagram_marker_text.py", line=1, note="fixture")
_STAMP = "diagram-engine"
# The house A2 content box is 1868 x 1248 G in a 12 x 8 frame: a column is 155.7 G wide, a row 156.


def _item(tag: str) -> Item:
    key = ("cable", tag)
    return Item(
        id=make_id(Item, key),
        key=key,
        part=None,
        parent=None,
        position=None,
        tag=tag,
        description="",
    )


def _unit() -> tuple[UnitRelease, Unit]:
    release = UnitRelease(
        id=make_id(UnitRelease, ("release",)),
        key=("release",),
        name="board",
        version=1,
        revision=1,
        interface="1",
    )
    return release, Unit(id=make_id(Unit, ("u",)), key=("u",), release=release.id, parent=None)


def _sheet(tag: str, unit: Any, number: int) -> DiagramSheet:
    key = ("sheet", tag)
    return DiagramSheet(
        id=make_id(DiagramSheet, key), key=key, unit=unit, number=number, produced_by=_STAMP
    )


def _marker(sheet: DiagramSheet, cable: Item, at: int, x: int, y: int) -> list[Any]:
    """A marker on `sheet` at (x, y) naming sheet `at`, with the line it ends."""
    ref = BoxRef(unit=None, item=cable.id)
    line_key = (*sheet.key, "line", cable.key[-1], "a", "b")
    points = (RoutePoint(index=0, x=x - 8, y=y), RoutePoint(index=1, x=x, y=y))
    line = DiagramLine(
        id=make_id(DiagramLine, line_key),
        key=line_key,
        sheet=sheet.id,
        cable=cable.id,
        a=ref,
        b=ref,
        points=points,
        text_x=x,
        text_y=y,
        produced_by=_STAMP,
    )
    key = (*sheet.key, "marker", cable.key[-1], "a", "b")
    marker = DiagramMarker(
        id=Id(kind="layout.diagram_marker", value="0" * 32)
        if sheet.unit
        else make_id(DiagramMarker, key),
        key=key,
        sheet=sheet.id,
        line=line.id,
        at_sheet=at,
        x=x,
        y=y,
        produced_by=_STAMP,
    )
    return [line, marker]


def _texts() -> dict[tuple[str, str], str]:
    """Two sheets of the system reading, two cut cables, and a decoy sheet 2 of a unit."""
    release, unit = _unit()
    one, two, decoy = _sheet("1", None, 1), _sheet("2", None, 2), _sheet("3", unit.id, 2)
    w1, w2 = _item("W1"), _item("W2")
    records = [release, unit, w1, w2, one, two, decoy]
    records += _marker(one, w1, 2, 1700, 20) + _marker(two, w1, 1, 40, 400)
    records += _marker(one, w2, 2, 1700, 700) + _marker(two, w2, 1, 40, 1200)
    records += _marker(decoy, w1, 1, 900, 800)
    draft = Draft()
    draft.extend(records, origin=_ORIGIN)
    model: Model = freeze(draft)
    return {
        (m.key[1], m.key[3]): diagram_marker_text(model, m)
        for m in layout_of(model, DiagramMarker).values()
        if m.key[1] != "3"
    }


def test_a_marker_prints_the_place_of_its_partner_on_the_other_sheet() -> None:
    texts = _texts()
    assert texts["1", "W1"] == "p2:1C"
    assert texts["2", "W1"] == "p1:11A"


def test_two_cut_lines_of_one_pair_of_sheets_name_their_own_partners() -> None:
    assert _texts()["1", "W2"] == "p2:1H"


def test_a_marker_of_another_reading_is_not_its_partner() -> None:
    """The decoy's id sorts first, so a lookup that ignores the reading would pick it."""
    assert _texts()["1", "W1"] == "p2:1C"
