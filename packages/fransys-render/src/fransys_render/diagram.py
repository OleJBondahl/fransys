"""Placed block diagrams to SVG, one full sheet per `fransys_layout.PlacedSheet` (render-0009)."""

from typing import TYPE_CHECKING

from symdef import group_mm, sheet_svg

from fransys_layout.symbols import text_room_on
from fransys_model.derive import DiagramSheet, diagram_sheet_key
from fransys_model.derive.block_diagram import box_lines, diagram_lines
from fransys_model.layout import sheet_for
from fransys_model.vocab import PageKind

from ._cable_pen import Pen
from ._constants import DIAGRAM_TEXT_PAD_G
from ._diagram_boxes import box_parts
from ._diagram_lines import line_parts, marker_parts
from ._library import smallest_height_mm

if TYPE_CHECKING:
    from electrical_symbols import Library
    from fransys_layout import DiagramLayout, PlacedDiagram, PlacedSheet
    from fransys_model.kernel import Model


def _sheet_body(model: Model, pen: Pen, diagram: PlacedDiagram, sheet: PlacedSheet) -> str:
    """The diagram of one sheet in content-box grid units: boxes, lines, then markers."""
    unit = diagram.unit
    reading = diagram_lines(model, unit)
    tabs = {(line.cable, line.a): line.tab_a for line in reading}
    tabs |= {(line.cable, line.b): line.tab_b for line in reading}
    names = {(line.cable, line.a, line.b): line.designation for line in reading}
    lines = sheet.lines
    body = [box_parts(pen, box, box_lines(model, box.box, unit), lines, tabs) for box in sheet.boxes]
    body += [line_parts(pen, ln, names[ln.cable, ln.a, ln.b]) for ln in lines]
    by_ends = {(ln.cable, ln.a, ln.b): ln for ln in lines}
    numbered = {other.number: other for other in diagram.sheets}
    for marker in sheet.markers:
        ends = (marker.cable, marker.a, marker.b)
        partner = next(m for m in numbered[marker.at_sheet].markers if (m.cable, m.a, m.b) == ends)
        seat = (DiagramSheet(unit=unit, number=sheet.number), (partner.x, partner.y))
        body.append(marker_parts(model, pen, marker, by_ends[ends], seat))
    return "".join(body)


def _render_sheet(model: Model, library: Library, diagram: PlacedDiagram, sheet: PlacedSheet) -> str:
    """One sheet's SVG at full sheet size; the diagram sits at the content box offset."""
    page = sheet_for(model, PageKind.BLOCK_DIAGRAM)
    pen = Pen(library, page.module_mm, smallest_height_mm(library), DIAGRAM_TEXT_PAD_G, text_room_on(model, page, library))
    body = group_mm(_sheet_body(model, pen, diagram, sheet), (page.content_x_mm, page.content_y_mm))
    return sheet_svg(page.width_mm, page.height_mm, body, margin_mm=0)


def diagram_sheets(model: Model, library: Library, diagrams: DiagramLayout) -> frozendict[str, str]:
    """Render every block-diagram sheet of `diagrams` to SVG.

    One SVG per placed sheet, keyed `diagram_sheet_key`, in the engine's order. Each is the
    whole A2 sheet in mm with the diagram at the content box; the frame, grid and title block
    are pdf's. Every text is a `derive.block_diagram` function's. Pure.
    """
    return frozendict(
        {
            diagram_sheet_key(DiagramSheet(unit=diagram.unit, number=sheet.number)): _render_sheet(model, library, diagram, sheet)
            for diagram in diagrams.diagrams
            for sheet in diagram.sheets
        }
    )
