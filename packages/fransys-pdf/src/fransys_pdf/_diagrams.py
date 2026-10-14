"""The BLOCK_DIAGRAM section: one A2 page per `DiagramSheet` of the reading (pdf-0023)."""

from typing import TYPE_CHECKING

from fransys_model.derive import (
    diagram_sheets,
    document_unit,
    page_destination,
    sheet_counter_text,
    sheet_text,
)
from fransys_model.derive.block_diagram import diagram_lines
from fransys_model.derive.page_nav import outline_sheets
from fransys_model.kernel import render_id
from fransys_model.layout import sheet_for
from fransys_model.vocab import DocumentPreset, PageKind

from ._frame import TitleBlockFields, background
from ._geometry import document_facts, project_notice, subject_label
from ._labels import sheet_label
from ._marks import sheet_mark
from ._sizes import sizes_of
from ._typst import literal

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_model.kernel import Model
    from fransys_model.vocab import Document


def diagram_source(model: Model, record: Document, svgs: Mapping[str, str]) -> str:
    """The section text: an A2 `#page` per sheet that has an SVG, `""` with none (pdf-0023)."""
    found = diagram_sheets(model, record)
    sheet = sheet_for(model, PageKind.BLOCK_DIAGRAM)
    size = f"width: {sheet.width_mm}mm, height: {sheet.height_mm}mm"
    pages = []
    outline = {entry.destination: entry for entry in outline_sheets(model, found)}
    for diagram in found:
        if (svg := svgs.get(render_id(diagram.id))) is None:
            continue
        fields = TitleBlockFields(
            *document_facts(model, record),
            page_title="Block diagram",
            scope=subject_label(model, record),
            sheet_counter=sheet_counter_text(diagram, len(found)),
            notice=project_notice(model),
            logo=record.logo,
        )
        mark = sheet_mark(outline[page_destination(model, diagram)])
        image = f'#image(bytes({literal(svg)}), format: "svg")'
        back = background(sheet, fields, sizes_of(model, record))
        numbering, start = sheet_label(sheet_text(model, diagram))
        pages.append(
            f"#page({size}, margin: 0mm, background: {back}{numbering})[{start}{mark}{image}]"
        )
    return "\n#pagebreak()\n".join(pages)


def diagram_no_drawings_messages(
    model: Model, record: Document, pages: tuple[PageKind, ...], svgs: Mapping[str, str]
) -> list[str]:
    """Why a kept BLOCK_DIAGRAM page lacks its drawing; none when it is drawn or has no line."""
    unit = None if record.preset is DocumentPreset.SYSTEM else document_unit(model, record)
    reading = record.preset is DocumentPreset.SYSTEM or unit is not None
    if PageKind.BLOCK_DIAGRAM not in pages or not reading or not diagram_lines(model, unit):
        return []
    found = diagram_sheets(model, record)
    if not found:
        return ["BLOCK_DIAGRAM: the diagram has lines but could not be drawn"]
    missing = [render_id(d.id) for d in found if render_id(d.id) not in svgs]
    return [f"BLOCK_DIAGRAM: missing drawing for {', '.join(missing)}"] if missing else []
