"""Private to `write/`: the records of one placed sheet, keyed by its reading and number."""

from typing import TYPE_CHECKING, Any

from fransys_layout.geometry import LayoutError
from fransys_model.kernel import make_id, render_id
from fransys_model.layout import (
    BoxRef,
    DiagramBox,
    DiagramLine,
    DiagramMarker,
    DiagramSheet,
    RoutePoint,
    Side,
    TabCell,
)

if TYPE_CHECKING:
    from fransys_layout.engines.diagram.values import (
        Ident,
        PlacedBox,
        PlacedLine,
        PlacedMarker,
        PlacedSheet,
        PlacedTab,
    )
    from fransys_model.kernel import AuthoringKey, Id


def _ref(box: Ident) -> BoxRef:
    if box.kind == "unit":
        return BoxRef(unit=box, item=None)
    return BoxRef(unit=None, item=box)


def _tab(index: int, tab: PlacedTab) -> TabCell:
    return TabCell(
        index=index,
        line=tab.cable,
        side=Side[tab.side.name],
        y=tab.y,
        text_width=tab.text_width,
    )


def _box(box: PlacedBox, sheet_key: AuthoringKey, sheet: Id[Any], stamp: str) -> DiagramBox:
    key = (*sheet_key, "box", render_id(box.box))
    return DiagramBox(
        id=make_id(DiagramBox, key),
        key=key,
        sheet=sheet,
        subject=_ref(box.box),
        dashed=box.dashed,
        x=box.x,
        y=box.y,
        width=box.width,
        height=box.height,
        tabs=tuple(_tab(i, tab) for i, tab in enumerate(box.tabs)),
        produced_by=stamp,
    )


def _line_key(sheet_key: AuthoringKey, what: str, line: PlacedLine | PlacedMarker) -> AuthoringKey:
    ends = (render_id(line.cable), render_id(line.a), render_id(line.b))
    return (*sheet_key, what, *ends)


def _line(line: PlacedLine, sheet_key: AuthoringKey, sheet: Id[Any], stamp: str) -> DiagramLine:
    key = _line_key(sheet_key, "line", line)
    return DiagramLine(
        id=make_id(DiagramLine, key),
        key=key,
        sheet=sheet,
        cable=line.cable,
        a=_ref(line.a),
        b=_ref(line.b),
        points=tuple(RoutePoint(index=i, x=p.x, y=p.y) for i, p in enumerate(line.points)),
        text_x=line.text_x,
        text_y=line.text_y,
        produced_by=stamp,
    )


def _marker(
    marker: PlacedMarker, sheet_key: AuthoringKey, sheet: Id[Any], stamp: str
) -> DiagramMarker:
    key = _line_key(sheet_key, "marker", marker)
    line_key = _line_key(sheet_key, "line", marker)
    line = make_id(DiagramLine, line_key)
    return DiagramMarker(
        id=make_id(DiagramMarker, key),
        key=key,
        sheet=sheet,
        line=line,
        at_sheet=marker.at_sheet,
        x=marker.x,
        y=marker.y,
        produced_by=stamp,
    )


def _check_markers(sheet: PlacedSheet) -> None:
    lines = {(line.cable, line.a, line.b) for line in sheet.lines}
    for marker in sheet.markers:
        if (marker.cable, marker.a, marker.b) not in lines:
            msg = f"sheet {sheet.number} has a marker with no line of the same cable and ends"
            raise LayoutError(msg)


def sheet_records(unit: Ident | None, sheet: PlacedSheet, stamp: str) -> list[Any]:
    """The `DiagramSheet`, its boxes, its lines and its markers."""
    owner = () if unit is None else ("unit", render_id(unit))
    key = ("layout", "diagram", "sheet", *owner, str(sheet.number))
    sheet_id = make_id(DiagramSheet, key)
    _check_markers(sheet)
    head = DiagramSheet(
        id=sheet_id,
        key=key,
        unit=unit,
        number=sheet.number,
        produced_by=stamp,
    )
    return [
        head,
        *(_box(b, key, sheet_id, stamp) for b in sheet.boxes),
        *(_line(line, key, sheet_id, stamp) for line in sheet.lines),
        *(_marker(m, key, sheet_id, stamp) for m in sheet.markers),
    ]
