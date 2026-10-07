"""The BLOCK_DIAGRAM section: one A2 page per `DiagramSheet` of the reading (pdf-0023)."""

from typing import TYPE_CHECKING

from fransys_model.derive import document_unit
from fransys_model.derive.block_diagram import diagram_lines
from fransys_model.kernel import render_id
from fransys_model.layout import DiagramSheet, layout_of, sheet_for
from fransys_model.vocab import DocumentPreset, PageKind

from ._frame import TitleBlockFields, background
from ._geometry import document_facts, project_notice, subject_label
from ._typst import literal

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_model.kernel import Model
    from fransys_model.vocab import Document


def diagram_sheets_for(model: Model, record: Document) -> tuple[DiagramSheet, ...]:
    """The diagram sheets of the document's reading, by number: SYSTEM's absolute or its unit's."""
    if record.preset is DocumentPreset.SYSTEM:
        unit = None
    elif (unit := document_unit(model, record)) is None:
        return ()
    found = (sheet for sheet in layout_of(model, DiagramSheet).values() if sheet.unit == unit)
    return tuple(sorted(found, key=lambda sheet: sheet.number))


def diagram_source(model: Model, record: Document, svgs: Mapping[str, str]) -> str:
    """The section text: an A2 `#page` per sheet that has an SVG, `""` with none (pdf-0023)."""
    found = diagram_sheets_for(model, record)
    sheet = sheet_for(model, PageKind.BLOCK_DIAGRAM)
    size = f"width: {sheet.width_mm}mm, height: {sheet.height_mm}mm"
    pages = []
    for diagram in found:
        if (svg := svgs.get(render_id(diagram.id))) is None:
            continue
        fields = TitleBlockFields(
            *document_facts(model, record),
            page_title="Block diagram",
            scope=subject_label(model, record),
            sheet_counter=f"{diagram.number} / {len(found)}",
            notice=project_notice(model),
            logo=record.logo,
        )
        image = f'#image(bytes({literal(svg)}), format: "svg")'
        pages.append(
            f"#page({size}, margin: 0mm, background: {background(sheet, fields)})[{image}]"
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
    found = diagram_sheets_for(model, record)
    if not found:
        return ["BLOCK_DIAGRAM: the diagram has lines but could not be drawn"]
    missing = [render_id(d.id) for d in found if render_id(d.id) not in svgs]
    return [f"BLOCK_DIAGRAM: missing drawing for {', '.join(missing)}"] if missing else []
