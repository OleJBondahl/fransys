"""Laid-out block diagrams to SVG, one full sheet per `layout.diagram_sheet` (BD7, render-0009)."""

from collections import defaultdict
from typing import TYPE_CHECKING, NamedTuple

from fransys_model.derive.block_diagram import box_lines, diagram_lines
from fransys_model.kernel import render_id
from fransys_model.layout import (
    DiagramBox,
    DiagramLine,
    DiagramMarker,
    DiagramSheet,
    layout_of,
    profile_of,
    sheet_for,
)
from fransys_model.vocab import PageKind

from ._cable_pen import Pen
from ._constants import DIAGRAM_TEXT_PAD_G
from ._diagram_boxes import box_parts, ref_id
from ._diagram_lines import line_parts, marker_parts
from ._style import style_block

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model


class _Found(NamedTuple):
    """The box, line and marker records of every sheet."""

    boxes: dict[Id[DiagramSheet], tuple[DiagramBox, ...]]
    lines: dict[Id[DiagramSheet], tuple[DiagramLine, ...]]
    markers: dict[Id[DiagramSheet], tuple[DiagramMarker, ...]]


def _order(sheet: DiagramSheet) -> tuple[str, int]:
    """Sheets by reading (the absolute one first), then number."""
    return ("" if sheet.unit is None else render_id(sheet.unit), sheet.number)


def _by_sheet[R: (DiagramBox, DiagramLine, DiagramMarker)](
    model: Model, kind: type[R]
) -> dict[Id[DiagramSheet], tuple[R, ...]]:
    """The `kind` records grouped by sheet, each group ordered by `id`."""
    groups: dict[Id[DiagramSheet], list[R]] = defaultdict(list)
    for record in sorted(layout_of(model, kind).values(), key=lambda r: r.id):
        groups[record.sheet].append(record)
    return {sheet: tuple(records) for sheet, records in groups.items()}


def _sheet_body(model: Model, pen: Pen, sheet: DiagramSheet, found: _Found) -> str:
    """The diagram of one sheet in content-box grid units: boxes, lines, then markers."""
    reading = diagram_lines(model, sheet.unit)
    tabs = {(line.cable, line.a): line.tab_a for line in reading}
    tabs |= {(line.cable, line.b): line.tab_b for line in reading}
    names = {(line.cable, line.a, line.b): line.designation for line in reading}
    lines = found.lines.get(sheet.id, ())
    body = [
        box_parts(pen, box, box_lines(model, ref_id(box.subject), sheet.unit), lines, tabs)
        for box in found.boxes.get(sheet.id, ())
    ]
    body += [line_parts(pen, ln, names[ln.cable, ref_id(ln.a), ref_id(ln.b)]) for ln in lines]
    by_id = {ln.id: ln for ln in lines}
    body += [marker_parts(model, pen, m, by_id[m.line]) for m in found.markers.get(sheet.id, ())]
    return "".join(body)


def _render_sheet(model: Model, sheet: DiagramSheet, found: _Found) -> str:
    """One sheet's SVG at full sheet size (BD7); the diagram sits at the content box offset."""
    page = sheet_for(model, PageKind.BLOCK_DIAGRAM)
    pen = Pen(page.module_mm, profile_of(model).text_height, DIAGRAM_TEXT_PAD_G)
    offset = f"{page.content_x_mm} {page.content_y_mm}"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{page.width_mm}mm" '
        f'height="{page.height_mm}mm" viewBox="0 0 {page.width_mm} {page.height_mm}">'
        f'{style_block(page.module_mm)}<g transform="translate({offset})">'
        f"{_sheet_body(model, pen, sheet, found)}</g></svg>"
    )


def diagram_sheets(model: Model) -> frozendict[str, str]:
    """Render every block-diagram sheet of a laid-out model to SVG.

    One SVG per `layout.diagram_sheet`, keyed `render_id(sheet.id)`, in `(unit, number)` order.
    Each is the whole A2 sheet in mm with the diagram at the content box; the frame, grid and
    title block are pdf's. Every text is a `derive.block_diagram` function's. Pure.
    """
    found = _Found(
        _by_sheet(model, DiagramBox), _by_sheet(model, DiagramLine), _by_sheet(model, DiagramMarker)
    )
    sheets = sorted(layout_of(model, DiagramSheet).values(), key=_order)
    return frozendict({render_id(sheet.id): _render_sheet(model, sheet, found) for sheet in sheets})
