"""The BLOCK_DIAGRAM section: one A2 page per `DiagramSheet` of the reading (pdf-0023)."""

from typing import TYPE_CHECKING

from fransys_model.derive import (
    SheetKey,
    diagram_sheet_key,
    diagram_sheets,
    document_scope,
    document_unit,
    kind_sheet,
    page_destination,
)
from fransys_model.derive.block_diagram import diagram_lines
from fransys_model.derive.page_nav import outline_sheets
from fransys_model.vocab import PageKind

from ._background import page_background
from ._labels import sheet_label
from ._marks import sheet_mark
from ._typst import literal

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_model.derive import DiagramSheet, DocumentRow, SheetBackground
    from fransys_model.kernel import Model


def diagram_source(
    model: Model,
    record: DocumentRow,
    svgs: Mapping[str, str],
    sheets: Mapping[SheetKey, SheetBackground],
    diagrams: tuple[DiagramSheet, ...],
) -> str:
    """The section text: an A2 `#page` per sheet that has an SVG, `""` with none (pdf-0023)."""
    found = diagram_sheets(model, record.id, diagrams)
    sheet = kind_sheet(model, PageKind.BLOCK_DIAGRAM)
    size = f"width: {sheet.width_mm}mm, height: {sheet.height_mm}mm"
    pages = []
    outline = {entry.destination: entry for entry in outline_sheets(model, found)}
    for index, diagram in enumerate(found):
        if (svg := svgs.get(diagram_sheet_key(diagram))) is None:
            continue
        entry = outline[page_destination(model, diagram)]
        image = f'#image(bytes({literal(svg)}), format: "svg")'
        key = SheetKey(record.id, PageKind.BLOCK_DIAGRAM, index)
        back = page_background(model, record, sheets, key)
        numbering, start = sheet_label(entry.number)
        mark = sheet_mark(entry)
        pages.append(f"#page({size}, margin: 0mm, background: {back}{numbering})[{start}{mark}{image}]")
    return "\n#pagebreak()\n".join(pages)


def diagram_no_drawings_messages(
    model: Model,
    record: DocumentRow,
    svgs: Mapping[str, str],
    found: tuple[DiagramSheet, ...],
) -> list[str]:
    """Why a kept BLOCK_DIAGRAM page lacks its drawing; none when it is drawn or has no line."""
    unit = document_unit(model, record.id)  # None for the SYSTEM document: it has no subject
    reading = document_scope(model, record.id).top_level or unit is not None
    lines = diagram_lines(model, unit) if reading else ()
    if not lines:
        return []
    if not found:
        return ["BLOCK_DIAGRAM: the diagram has lines but could not be drawn (no finding names the cause)"]
    missing = [key for d in found if (key := diagram_sheet_key(d)) not in svgs]
    return [f"BLOCK_DIAGRAM: missing drawing for {', '.join(missing)}"] if missing else []
