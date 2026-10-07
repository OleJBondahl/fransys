"""The lines and cut markers of a diagram sheet (BD5, BD7): records drawn, texts from derive."""

from typing import TYPE_CHECKING

from fransys_model.derive.block_diagram import diagram_marker_text

from ._constants import DIAGRAM_MARKER_DEPTH_G, DIAGRAM_MARKER_GAP_G, DIAGRAM_MARKER_HALF_G

if TYPE_CHECKING:
    from fransys_model.kernel import Model
    from fransys_model.layout import DiagramLine, DiagramMarker

    from ._cable_pen import Pen


def line_parts(pen: Pen, line: DiagramLine, designation: str) -> str:
    """One line as a polyline, its designation centred on the record's text place."""
    points = tuple((p.x, p.y) for p in line.points)
    top = line.text_y - pen.font_g // 2
    return pen.polyline("diagram-line", points) + pen.text(
        "line", (line.text_x, top), designation, middle=True
    )


def marker_parts(model: Model, pen: Pen, marker: DiagramMarker, line: DiagramLine) -> str:
    """A cut marker: an arrow at the line end, the partner's place printed past it."""
    last, before = line.points[-1], line.points[-2]
    sign = 1 if last.x > before.x else -1
    back = marker.x - sign * DIAGRAM_MARKER_DEPTH_G
    tip = (marker.x, marker.y)
    above, below = (
        (back, marker.y - DIAGRAM_MARKER_HALF_G),
        (back, marker.y + DIAGRAM_MARKER_HALF_G),
    )
    at = (marker.x + sign * DIAGRAM_MARKER_GAP_G, marker.y - pen.font_g // 2)
    arrow = pen.polyline("marker", (tip, above, below, tip))
    return arrow + pen.text("marker-label", at, diagram_marker_text(model, marker), end=sign < 0)
