"""The lines and cut markers of a diagram sheet: placed values drawn, texts from derive."""

from typing import TYPE_CHECKING

from fransys_layout.symbols import frame_cell
from fransys_model.derive.block_diagram import diagram_marker_text
from fransys_model.layout import sheet_for
from fransys_model.vocab import PageKind

from ._constants import DIAGRAM_MARKER_DEPTH_G, DIAGRAM_MARKER_GAP_G, DIAGRAM_MARKER_HALF_G

if TYPE_CHECKING:
    from fransys_layout import DiagramLine, PlacedMarker
    from fransys_model.derive import DiagramSheet
    from fransys_model.kernel import Model

    from ._cable_pen import Pen


def line_parts(pen: Pen, line: DiagramLine, designation: str) -> str:
    """One line as a polyline, its designation centred on its text place."""
    points = tuple((p.x, p.y) for p in line.points)
    top = line.text_y - pen.font_g // 2
    return pen.wire("diagram_line", points) + pen.text("line", (line.text_x, top), designation, middle=True)


def marker_parts(
    model: Model,
    pen: Pen,
    marker: PlacedMarker,
    line: DiagramLine,
    seat: tuple[DiagramSheet, tuple[int, int]],
) -> str:
    """A cut marker: an arrow at the line end, the partner's place printed past it.

    `seat` is the marker's own sheet and its partner marker's `(x, y)`.
    """
    last, before = line.points[-1], line.points[-2]
    sign = 1 if last.x > before.x else -1
    back = marker.x - sign * DIAGRAM_MARKER_DEPTH_G
    tip = (marker.x, marker.y)
    above, below = (
        (back, marker.y - DIAGRAM_MARKER_HALF_G),
        (back, marker.y + DIAGRAM_MARKER_HALF_G),
    )
    at = (marker.x + sign * DIAGRAM_MARKER_GAP_G, marker.y - pen.font_g // 2)
    arrow = pen.wire("marker", (tip, above, below, tip))
    column, row = frame_cell(pen.library, sheet_for(model, PageKind.BLOCK_DIAGRAM), *seat[1])
    text = diagram_marker_text(model, seat[0], marker.at_sheet, column, row)
    return arrow + pen.text("marker-label", at, text, end=sign < 0)
