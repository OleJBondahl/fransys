"""Document assembly to Typst source."""

from functools import partial
from typing import TYPE_CHECKING

from fransys_model.derive import (
    PAGE_HEADINGS,
    SheetKey,
    document_page_kinds,
    document_row,
    document_sheet,
    harness_cables_for,
)
from fransys_model.vocab import PageKind

from ._background import page_background
from ._contents import contents_page
from ._diagrams import diagram_source
from ._drawings import harness_drawing_source, schematic_pages, schematic_source
from ._geometry import document_metadata, preamble, text_margin
from ._labels import LAST_PAGE, RESTART
from ._lists import (
    bom_page,
    cable_list_page,
    connector_list_page,
    designation_list_page,
    plc_list_page,
    terminal_list_page,
    wire_label_list_page,
)
from ._marks import list_mark
from ._pages import cover_page, notes_page
from ._schematic_yield import schematic_yields
from ._sheet_index import sheet_index_page
from ._sizes import sizes_of

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from fransys_model.derive import (
        BridgePiece,
        DocumentId,
        DocumentRow,
        SheetBackground,
        SheetRow,
    )
    from fransys_model.kernel import Model

_SELF_FRAMED = (PageKind.BLOCK_DIAGRAM, PageKind.SCHEMATIC, PageKind.HARNESS_DRAWING)


def _section_prefix(
    model: Model,
    record: DocumentRow,
    sheet: SheetRow,
    kind: PageKind,
    sheets: Mapping[SheetKey, SheetBackground],
) -> str:
    """`#set page(margin:, background:)` for every page of `kind` but `SCHEMATIC`."""
    back = page_background(model, record, sheets, SheetKey(record.id, kind, 0))
    return f"#set page(margin: {text_margin(sheet)}, background: {back})\n{RESTART}"


def _list_pages(bridges: Mapping[str, BridgePiece] | None) -> dict[PageKind, Callable[..., str]]:
    """Each list page kind's builder; the terminal list also takes the Bridge mark pieces."""
    return {
        PageKind.PLC_LIST: plc_list_page,
        PageKind.TERMINAL_LIST: partial(terminal_list_page, bridges=bridges),
        PageKind.CONNECTOR_LIST: connector_list_page,
        PageKind.WIRE_LABEL_LIST: wire_label_list_page,
        PageKind.DESIGNATION_LIST: designation_list_page,
        PageKind.BOM: bom_page,
    }


def _text_page(  # noqa: PLR0913, PLR0917 -- one branch per `PageKind`, plus `sheets` and `bridges`
    kind: PageKind,
    model: Model,
    record: DocumentRow,
    pages: tuple[PageKind, ...],
    sheets: Mapping[SheetKey, SheetBackground],
    bridges: Mapping[str, BridgePiece] | None,
) -> str:
    if kind is PageKind.COVER:
        return cover_page(model, record)
    if kind is PageKind.NOTES:
        return notes_page(record)
    if kind is PageKind.SHEET_INDEX:
        return sheet_index_page(model, record, pages, sheets)
    if kind is PageKind.CONTENTS:
        return contents_page(model, record, pages)
    if kind is PageKind.CABLE_LIST:
        return cable_list_page(model, record)
    body = _list_pages(bridges)[kind](model, record)
    return list_mark(body, PAGE_HEADINGS[kind])


def _page_source(  # noqa: PLR0913, PLR0917 -- one branch per `PageKind`, plus `sheet` and `sheets` for the page background
    kind: PageKind,
    model: Model,
    record: DocumentRow,
    svgs: Mapping[str, str],
    pages: tuple[PageKind, ...],
    sheet: SheetRow,
    sheets: Mapping[SheetKey, SheetBackground],
    bridges: Mapping[str, BridgePiece] | None,
) -> str:
    """The Typst source of one page kind; the two drawing kinds set their own frame."""
    if kind is PageKind.SCHEMATIC:
        if schematic_yields(model, record, pages):  # pdf-0033: no drawing set, no page
            return ""
        found = schematic_pages(model, record, pages)
        return schematic_source(model, record, sheet, found, svgs, sheets)
    if kind is PageKind.HARNESS_DRAWING:
        cables = harness_cables_for(model, record.id, pages)
        return harness_drawing_source(model, record, sheet, cables, svgs, sheets)
    if kind is PageKind.BLOCK_DIAGRAM:
        return diagram_source(model, record, svgs, sheets)
    return _text_page(kind, model, record, pages, sheets, bridges)


def source(
    model: Model,
    document: DocumentId,
    svgs: Mapping[str, str],
    sheets: Mapping[SheetKey, SheetBackground],
    bridges: Mapping[str, BridgePiece] | None = None,
) -> str:
    """The complete, self-contained Typst source of one document.

    Args:
        model: A laid-out model.
        document: Id of the document.
        svgs: Page key to SVG text (``fransys_render.pages``): each `SCHEMATIC` SVG is inlined as
            an `image`; a `HARNESS_DRAWING` page reads one per cable block (`cable_block_key`).
        sheets: Page key to its background (``fransys_render.sheets``): frame, grid and title
            block as one SVG, and the boxes for the page counter and the logo.
        bridges: ``fransys_render.bridge_pieces()``; a jumper group without it is a `KeyError`.

    Returns:
        The Typst source, pure in `model`, `svgs` and `sheets`; each page's background is its
        sheet. An empty section body is skipped, not joined as a bare `#pagebreak()`.
    """
    record = document_row(model, document)
    pages = document_page_kinds(model, document)
    sheet = document_sheet(model, record.id, pages)
    page_bodies = []
    for kind in pages:
        body = _page_source(kind, model, record, svgs, pages, sheet, sheets, bridges)
        if not body:
            continue
        if kind not in _SELF_FRAMED:
            body = _section_prefix(model, record, sheet, kind, sheets) + "\n" + body
        page_bodies.append(body)
    head = document_metadata(model, record) + "\n" + preamble(sizes_of(model, record.id), sheet)
    body = "\n#pagebreak()\n".join(page_bodies)
    return f"{head}\n{body}\n#metadata(none) <{LAST_PAGE}>\n"
