"""Document assembly to Typst source (spec P1, P4, P5, P10; page-frame R1-R6)."""

from typing import TYPE_CHECKING

from fransys_model.vocab import PageKind, documents

from ._contents import contents_page
from ._drawings import harness_cables_for, harness_drawing_source, schematic_pages, schematic_source
from ._frame import TitleBlockFields, background, text_margin
from ._geometry import (
    document_facts,
    document_metadata,
    preamble,
    project_notice,
    resolve_sheet_format,
    subject_label,
)
from ._lists import (
    bom_page,
    cable_list_page,
    connector_list_page,
    designation_list_page,
    plc_list_page,
    terminal_list_page,
    wire_label_list_page,
)
from ._pages import cover_page, notes_page
from .presets import page_kinds

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_model.kernel import Id, Model
    from fransys_model.layout import SheetFormat
    from fransys_model.vocab import Document

# The page kind's own heading, its title-block `page_title` (page-frame R3). SCHEMATIC and
# HARNESS_DRAWING are not here: each of their own pages carries its own title and scope
# instead of one shared per kind (`schematic_source`, `harness_drawing_source`).
_HEADING_WORDS: dict[PageKind, str] = {
    PageKind.COVER: "Cover",
    PageKind.NOTES: "Notes",
    PageKind.CONTENTS: "Contents",
    PageKind.PLC_LIST: "PLC list",
    PageKind.TERMINAL_LIST: "Terminal list",
    PageKind.CONNECTOR_LIST: "Connector list",
    PageKind.WIRE_LABEL_LIST: "Wire label list",
    PageKind.DESIGNATION_LIST: "Designation list",
    PageKind.CABLE_LIST: "Cable list",
    PageKind.BOM: "BOM",
}


def _section_prefix(model: Model, record: Document, sheet: SheetFormat, kind: PageKind) -> str:
    """`#set page(margin:, background:)` for every page of `kind` but `SCHEMATIC` (R3, R4)."""
    fields = TitleBlockFields(
        *document_facts(model, record),
        page_title=_HEADING_WORDS[kind],
        scope=subject_label(model, record),
        sheet_counter="",
        notice=project_notice(model),
        logo=record.logo,
    )
    return f"#set page(margin: {text_margin(sheet)}, background: {background(sheet, fields)})"


_LIST_PAGES = {
    PageKind.PLC_LIST: plc_list_page,
    PageKind.TERMINAL_LIST: terminal_list_page,
    PageKind.CONNECTOR_LIST: connector_list_page,
    PageKind.WIRE_LABEL_LIST: wire_label_list_page,
    PageKind.DESIGNATION_LIST: designation_list_page,
    PageKind.BOM: bom_page,
}


def _text_page(kind: PageKind, model: Model, record: Document, pages: tuple[PageKind, ...]) -> str:
    if kind is PageKind.COVER:
        return cover_page(model, record)
    if kind is PageKind.NOTES:
        return notes_page(record)
    if kind is PageKind.CONTENTS:
        return contents_page(model, record, pages)
    if kind is PageKind.CABLE_LIST:
        return cable_list_page(model)
    return _LIST_PAGES[kind](model, record)


def _page_source(  # noqa: PLR0913, PLR0917 -- one branch per `PageKind`, plus `sheet` for the page-frame background
    kind: PageKind,
    model: Model,
    record: Document,
    svgs: Mapping[str, str],
    pages: tuple[PageKind, ...],
    sheet: SheetFormat,
) -> str:
    """The Typst source of one page kind; the two drawing kinds set their own frame (R3, R4)."""
    if kind is PageKind.SCHEMATIC:
        return schematic_source(model, record, sheet, schematic_pages(model, record, pages), svgs)
    if kind is PageKind.HARNESS_DRAWING:
        cables = harness_cables_for(model, record, pages)
        return harness_drawing_source(model, record, sheet, cables, svgs)
    return _text_page(kind, model, record, pages)


def source(model: Model, document: Id[Document], svgs: Mapping[str, str]) -> str:
    """The complete, self-contained Typst source of one document.

    Args:
        model: A laid-out model.
        document: Id of the authored `Document` record.
        svgs: Page key to SVG text (from ``fransys_render.pages``); each `SCHEMATIC` SVG is
            inlined as ``image(bytes("..."), format: "svg")``. A `HARNESS_DRAWING` page reads
            one SVG per cable block, keyed by `cable_block_key` (pdf-0022).

    Returns:
        The Typst source, pure in `model` and `svgs`. Every page carries frame, grid and title
        block as its Typst background (page-frame R1). An empty section body is skipped, not
        joined as a bare `#pagebreak()`.
    """
    record = documents(model)[document]
    pages = document_pages(model, document)
    sheet = resolve_sheet_format(model, record, pages)
    page_bodies = []
    for kind in pages:
        body = _page_source(kind, model, record, svgs, pages, sheet)
        if not body:
            continue
        if kind not in (PageKind.SCHEMATIC, PageKind.HARNESS_DRAWING):
            body = _section_prefix(model, record, sheet, kind) + "\n" + body
        page_bodies.append(body)
    head = document_metadata(model, record) + "\n" + preamble(sheet)
    return head + "\n" + "\n#pagebreak()\n".join(page_bodies) + "\n"


def document_pages(model: Model, document: Id[Document]) -> tuple[PageKind, ...]:
    """The pages one document will contain, in order.

    `page_kinds` of the document record's preset, additions and removals, with NOTES dropped
    when the record has no notes text. `source` assembles exactly these pages.

    Args:
        model: A frozen model.
        document: Id of the authored `Document` record.

    Returns:
        The page kinds in canonical order. Pure.
    """
    record = documents(model)[document]
    resolved = page_kinds(record.preset, add=record.add, remove=record.remove)
    if record.notes is None:
        resolved = tuple(kind for kind in resolved if kind is not PageKind.NOTES)
    return resolved
