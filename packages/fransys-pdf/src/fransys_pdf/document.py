"""Document assembly to Typst source."""

from functools import partial
from typing import TYPE_CHECKING

from fransys_model.derive import (
    ListKey,
    PageForm,
    SheetKey,
    document_page_kinds,
    document_row,
    document_sheet,
    font_family,
    harness_cables_for,
    page_headings,
    page_preset,
)

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
        BridgePieceRow,
        DocumentId,
        DocumentRow,
        PageId,
        SheetBackground,
        SheetRow,
    )
    from fransys_model.derive.page_nav import ReferenceLink
    from fransys_model.kernel import Model
    from fransys_model.vocab import PageKind


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


def _list_pages(
    bridges: Mapping[str, BridgePieceRow] | None,
    words: Mapping[str, str],
    share_pct: float,
    gutter_pct: float,
) -> dict[ListKey, Callable[..., str]]:
    """Each list key's builder; the terminal list also takes the Bridge mark pieces."""
    flow = {"share_pct": share_pct, "gutter_pct": gutter_pct}
    return {
        ListKey.PLC: partial(plc_list_page, **flow),
        ListKey.TERMINAL: partial(
            terminal_list_page, bridges=bridges, bridge_word=words["bridge"], **flow
        ),
        ListKey.CONNECTOR: partial(connector_list_page, **flow),
        ListKey.WIRE_LABEL: partial(wire_label_list_page, **flow),
        ListKey.DESIGNATION: partial(designation_list_page, **flow),
        ListKey.BOM: bom_page,
    }


def _text_page(  # noqa: PLR0913, PLR0917 -- one branch per `PageKind`, plus `sheets` and `bridges`
    kind: PageKind,
    model: Model,
    record: DocumentRow,
    pages: tuple[PageKind, ...],
    sheets: Mapping[SheetKey, SheetBackground],
    bridges: Mapping[str, BridgePieceRow] | None,
    words: Mapping[str, str],
    cover: Callable[[Model, DocumentRow], str],
    *,
    share_pct: float,
    gutter_pct: float,
) -> str:
    preset = page_preset(kind)
    if preset.form is PageForm.COVER:
        return cover(model, record)
    if preset.form is PageForm.NOTES:
        return notes_page(record, words["notes"])
    if preset.form is PageForm.SHEET_INDEX:
        headers = (words["sheet"], words["title"], words["page"])
        return sheet_index_page(
            model, record, pages, sheets, headers, share_pct=share_pct, gutter_pct=gutter_pct
        )
    if preset.form is PageForm.CONTENTS:
        return contents_page(model, record, pages)
    if preset.form is PageForm.CABLE_LIST:
        return cable_list_page(model, record)
    assert preset.list_key is not None  # noqa: S101 -- LIST is the last form and has a key
    body = _list_pages(bridges, words, share_pct, gutter_pct)[preset.list_key](model, record)
    return list_mark(body, page_headings(model)[kind])


def _page_source(  # noqa: PLR0913, PLR0917 -- one branch per `PageKind`, plus `sheet` and `sheets` for the page background
    kind: PageKind,
    model: Model,
    record: DocumentRow,
    svgs: Mapping[str, str],
    pages: tuple[PageKind, ...],
    sheet: SheetRow,
    sheets: Mapping[SheetKey, SheetBackground],
    bridges: Mapping[str, BridgePieceRow] | None,
    words: Mapping[str, str],
    cover: Callable[[Model, DocumentRow], str],
    *,
    links: Mapping[PageId, tuple[ReferenceLink, ...]],
    share_pct: float,
    gutter_pct: float,
) -> str:
    """The Typst source of one page kind; the two drawing kinds set their own frame."""
    form = page_preset(kind).form
    if form is PageForm.SCHEMATIC:
        if schematic_yields(model, record, pages):  # pdf-0033: no drawing set, no page
            return ""
        found = schematic_pages(model, record, pages)
        return schematic_source(model, record, sheet, found, svgs, sheets, links)
    if form is PageForm.HARNESS_DRAWING:
        cables = harness_cables_for(model, record.id, pages)
        return harness_drawing_source(model, record, sheet, cables, svgs, sheets)
    if form is PageForm.BLOCK_DIAGRAM:
        return diagram_source(model, record, svgs, sheets)
    return _text_page(
        kind,
        model,
        record,
        pages,
        sheets,
        bridges,
        words,
        cover,
        share_pct=share_pct,
        gutter_pct=gutter_pct,
    )


def source(  # noqa: PLR0913 -- the document's inputs, the two list-share values from `[pdf]` and the facade's words
    model: Model,
    document: DocumentId,
    svgs: Mapping[str, str],
    sheets: Mapping[SheetKey, SheetBackground],
    bridges: Mapping[str, BridgePieceRow] | None = None,
    *,
    links: Mapping[PageId, tuple[ReferenceLink, ...]],
    list_share_pct: float,
    list_gutter_pct: float,
    words: Mapping[str, str],
    revision_headers: tuple[str, ...],
    description_mm: float,
) -> str:
    """The complete, self-contained Typst source of one document, pure in its inputs.

    Args:
        model: A laid-out model.
        document: Id of the document.
        svgs: Page key to SVG text, inlined as an `image`.
        sheets: Page key to its background (``fransys_render.sheets``).
        bridges: ``fransys_render.bridge_pieces()``; a jumper group without it is a `KeyError`.
        links: Page id to its reference links; every drawn page is in it.
        list_share_pct: A list page's column, % of the content width.
        list_gutter_pct: The gutter between a list page's two columns, %.
        words: The printed words, by key (`pdf_texts`).
        revision_headers: The revision table's header cells.
        description_mm: The revision table's description column width.
    """
    record = document_row(model, document)
    pages = document_page_kinds(model, document)
    sheet = document_sheet(model, record.id, pages)
    cover = partial(cover_page, headers=revision_headers, description_mm=description_mm)
    page_bodies = []
    for kind in pages:
        body = _page_source(
            kind,
            model,
            record,
            svgs,
            pages,
            sheet,
            sheets,
            bridges,
            words,
            cover,
            links=links,
            share_pct=list_share_pct,
            gutter_pct=list_gutter_pct,
        )
        if not body:
            continue
        if not page_preset(kind).self_framed:
            body = _section_prefix(model, record, sheet, kind, sheets) + "\n" + body
        page_bodies.append(body)
    head = (
        document_metadata(model, record)
        + "\n"
        + preamble(sizes_of(model, record.id), sheet, font_family(model))
    )
    body = "\n#pagebreak()\n".join(page_bodies)
    return f"{head}\n{body}\n#metadata(none) <{LAST_PAGE}>\n"
