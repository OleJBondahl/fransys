"""Document assembly to Typst source."""

from functools import partial
from typing import TYPE_CHECKING, cast

from fransys_model.derive import (
    ListKey,
    PageForm,
    SheetKey,
    document_page_kinds,
    document_row,
    document_sheet,
    font_family,
    page_headings,
    page_preset,
)

from ._background import LAST_PAGE
from ._contents import contents_page
from ._diagrams import diagram_source
from ._doc import background
from ._drawings import harness_drawing_source, schematic_source
from ._geometry import document_metadata, preamble, text_margin
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
        DiagramSheet,
        DocumentId,
        DocumentRow,
        PageId,
        SheetBackground,
    )
    from fransys_model.derive.page_nav import ReferenceLink
    from fransys_model.kernel import Model
    from fransys_model.vocab import PageKind

    from ._doc import BridgeInputs, Doc


type _Texts = tuple[Callable[[Model, DocumentRow], str], Mapping[str, str], Mapping[str, BridgePieceRow] | None]


def _section_prefix(doc: Doc, kind: PageKind) -> str:
    """`#set page(margin:, background:)` for every page of `kind` but `SCHEMATIC`."""
    margin, back = text_margin(doc[3], doc[6]["page_margin_mm"]), background(doc, kind, 0)
    return f"#set page(margin: {margin}, background: {back})"


def _list_pages(doc: Doc, bridge: BridgeInputs, flow: dict[str, float]) -> dict[ListKey, Callable[[], str]]:
    """Each list key's builder over `doc`."""
    args = doc[:2]
    return {
        ListKey.PLC: partial(plc_list_page, *args, **flow),
        ListKey.TERMINAL: partial(terminal_list_page, *args, bridge, **flow),
        ListKey.CONNECTOR: partial(connector_list_page, *args, **flow),
        ListKey.WIRE_LABEL: partial(wire_label_list_page, *args, **flow),
        ListKey.DESIGNATION: partial(designation_list_page, *args, **flow),
        ListKey.BOM: partial(bom_page, *args),
    }


def _text_page(kind: PageKind, doc: Doc, texts: _Texts) -> str:
    model, record, pages, _, _, _, _ = doc
    cover, words, bridges = texts
    pdf = doc[6]
    flow = {"share_pct": pdf["list_share_pct"], "gutter_pct": pdf["list_gutter_pct"]}
    preset = page_preset(kind)
    if preset.form is PageForm.COVER:
        return cover(model, record)
    if preset.form is PageForm.NOTES:
        return notes_page(cast("str", record.notes), words["notes"])
    if preset.form is PageForm.SHEET_INDEX:
        headers = (words["title"], words["page"])
        return sheet_index_page(doc, headers, **flow)
    if preset.form is PageForm.CONTENTS:
        return contents_page(model, record, pages)
    if preset.form is PageForm.CABLE_LIST:
        return cable_list_page(model, record)
    body = _list_pages(doc, (words["bridge"], bridges, pdf["bridge_column_mm"]), flow)[cast("ListKey", preset.list_key)]()
    return list_mark(body, page_headings(model)[kind])


def _page_source(
    kind: PageKind,
    doc: Doc,
    texts: _Texts,
    svgs: Mapping[str, str],
    links: Mapping[PageId, tuple[ReferenceLink, ...]],
) -> str:
    """The Typst source of one page kind; the two drawing kinds set their own frame."""
    form = page_preset(kind).form
    if form is PageForm.SCHEMATIC:
        if schematic_yields(*doc[:3], doc[5]):  # pdf-0033: no drawing set, no page
            return ""
        return schematic_source(doc, svgs, links)
    if form is PageForm.HARNESS_DRAWING:
        return harness_drawing_source(doc, svgs)
    if form is PageForm.BLOCK_DIAGRAM:
        return diagram_source(*doc[:2], svgs, doc[4], doc[5])
    return _text_page(kind, doc, texts)


def source(  # noqa: PLR0913 -- the document's inputs, the facade's `[pdf]` table and its words [public keyword API kept, decision 0444]
    model: Model,
    document: DocumentId,
    svgs: Mapping[str, str],
    sheets: Mapping[SheetKey, SheetBackground],
    bridges: Mapping[str, BridgePieceRow] | None = None,
    *,
    links: Mapping[PageId, tuple[ReferenceLink, ...]],
    diagrams: tuple[DiagramSheet, ...],
    pdf: Mapping[str, float],
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
        diagrams: Every block diagram sheet the diagram engine placed (`DiagramSheet`).
        pdf: The `[pdf]` table: `list_share_pct`, `list_gutter_pct`, `page_margin_mm`, `cable_run_header_mm` and `bridge_column_mm`.
        words: The printed words, by key (`pdf_texts`).
        revision_headers: The revision table's header cells.
        description_mm: The revision table's description column width.
    """
    record = document_row(model, document)
    pages = document_page_kinds(model, document)
    doc = (model, record, pages, document_sheet(model, record.id, pages), sheets, diagrams, pdf)
    cover = partial(cover_page, headers=revision_headers, description_mm=description_mm)
    texts = (cover, words, bridges)
    page_bodies = []
    for kind in pages:
        body = _page_source(kind, doc, texts, svgs, links)
        if not body:
            continue
        if not page_preset(kind).self_framed:
            body = _section_prefix(doc, kind) + "\n" + body
        page_bodies.append(body)
    head = document_metadata(model, record) + "\n" + preamble(sizes_of(model), doc[3], font_family(model))
    body = "\n#pagebreak()\n".join(page_bodies)
    return f"{head}\n{body}\n#metadata(none) <{LAST_PAGE}>\n"
