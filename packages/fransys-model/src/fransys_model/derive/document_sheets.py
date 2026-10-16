"""A document's sheets: the title-block fields of every page background it prints (pdf-0046).

The page list, the fields and the keys are derive's, so render draws each sheet and checks its
text from the model alone and pdf looks the same sheet up by the same key.
"""

from collections import Counter

from fransys_kernel import render_id
from fransys_model.layout import SheetFormat, sheet_for, sheet_format_of
from fransys_model.vocab import PageKind
from fransys_model.vocab.tables import documents
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.layout import Page
lazy from fransys_model.vocab import Document

from .cable_runs import cable_runs
from .designation import item_designation
from .document_pages import drawn_pages
from .document_sizes import sizes_of
from .document_subject import scope_path, subject_label
from .harness_blocks import cable_blocks, harness_cables_for, system_has_no_top_level_cables
from .page_headings import DIAGRAM_TITLE, HARNESS_DRAWING_TITLE, PAGE_HEADINGS, SCHEMATIC_TITLE
from .page_presets import document_page_kinds
from .page_titles import page_title_forms
from .rows_sheet import TitleBlockFields
from .rows_sheet_pages import DocumentSheets, SheetPage
from .schematic_subject import has_schematic_subject
from .sheet_forms import sheet_counter_text
from .sheet_frame import sheet_frame
from .sheets import diagram_sheets
from .title_block import document_facts

__all__ = ["document_sheet_format", "document_sheets", "document_sheets_of", "sheet_key"]

_NONE = "none"


def sheet_key(document: Id[Document], kind: PageKind, index: int | str) -> str:
    """The key of one page background: the document, the page kind and the page's place in it."""
    return f"{render_id(document)}#{kind.name}#{index}"


def document_sheet_format(
    model: Model, record: Document, pages: tuple[PageKind, ...]
) -> SheetFormat:
    """The paper of every page: the first drawing-set page's format, else the top profile's sheet.

    A system document has none, so it takes the top profile's sheet, else the house one.
    """
    found = drawn_pages(model, record) if PageKind.SCHEMATIC in pages else ()
    if found:
        return sheet_format_of(model, found[0].sheet_format)
    return sheet_for(model, PageKind.COVER)


def _fields(
    model: Model,
    record: Document,
    forms: tuple[str, ...],
    *,
    scope: str | None = None,
    counter: str = "",
) -> TitleBlockFields:
    """The title block of a page: the document facts, its title forms and what the page adds."""
    return TitleBlockFields(
        *document_facts(model, record),
        page_title=forms[0],
        scope=scope_path(model, record) if scope is None else scope,
        sheet_counter=counter,
        notice=record.notice,
        logo=record.logo,
        page_title_shorter=forms[1:],
    )


def _drawing_fields(
    model: Model, record: Document, found: tuple[Page, ...]
) -> list[TitleBlockFields]:
    """Each drawing page's title block, `n / N` counted per drawing set."""
    scope = scope_path(model, record)
    totals = Counter(page.drawing_set for page in found)
    forms = [page_title_forms(model, page) for page in found]
    return [
        _fields(
            model,
            record,
            form,
            scope=scope,
            counter=sheet_counter_text(page, totals[page.drawing_set]),
        )
        for page, form in zip(found, forms, strict=True)
    ]


def _schematic_pages(model: Model, record: Document, sheet: SheetFormat) -> list[SheetPage]:
    kind = PageKind.SCHEMATIC
    found = drawn_pages(model, record)
    if not has_schematic_subject(record):
        found = ()
    out = [
        SheetPage(
            key=sheet_key(record.id, kind, i),
            kind=kind,
            sheet=sheet,
            fields=fields,
            where=f"page {page.number}",
            group=kind.name,
        )
        for i, (page, fields) in enumerate(
            zip(found, _drawing_fields(model, record, found), strict=True)
        )
    ]
    fallback = _fields(model, record, (SCHEMATIC_TITLE,))
    key = sheet_key(record.id, kind, _NONE)
    return [*out, SheetPage(key=key, kind=kind, sheet=sheet, fields=fallback, where="", group="")]


def _harness_scope(model: Model, record: Document) -> str:
    if record.item is not None:
        return item_designation(model, record.item)
    return subject_label(model, record)


def _harness_pages(
    model: Model, record: Document, pages: tuple[PageKind, ...], sheet: SheetFormat
) -> list[SheetPage]:
    kind = PageKind.HARNESS_DRAWING
    cables = harness_cables_for(model, record, pages)
    if system_has_no_top_level_cables(record, cables):
        return []
    blocks = cable_blocks(model, record, cables)
    if not blocks:
        key = sheet_key(record.id, kind, _NONE)
        fallback = _fields(model, record, (HARNESS_DRAWING_TITLE,))
        return [SheetPage(key=key, kind=kind, sheet=sheet, fields=fallback, where="", group="")]
    scope = _harness_scope(model, record)
    return [
        SheetPage(
            key=sheet_key(record.id, kind, i),
            kind=kind,
            sheet=sheet,
            fields=_fields(model, record, (run.heading,), scope=scope),
            where=run.heading,
            group=kind.name,
        )
        for i, run in enumerate(cable_runs(blocks))
    ]


def _diagram_pages(model: Model, record: Document) -> list[SheetPage]:
    kind = PageKind.BLOCK_DIAGRAM
    found = diagram_sheets(model, record)
    paper = sheet_for(model, kind)
    return [
        SheetPage(
            key=sheet_key(record.id, kind, i),
            kind=kind,
            sheet=paper,
            fields=_fields(
                model, record, (DIAGRAM_TITLE,), counter=sheet_counter_text(diagram, len(found))
            ),
            where="",
            group="",
        )
        for i, diagram in enumerate(found)
    ]


def document_sheets(model: Model, document: Id[Document]) -> DocumentSheets:
    """Every page background of `document`, in page order, with its paper and sizes."""
    record = documents(model)[document]
    kinds = document_page_kinds(model, document)
    sheet = document_sheet_format(model, record, kinds)
    first_section = next((kind for kind in kinds if kind in PAGE_HEADINGS), PageKind.COVER)
    pages: list[SheetPage] = []
    for kind in kinds:
        if kind is PageKind.SCHEMATIC:
            pages += _schematic_pages(model, record, sheet)
        elif kind is PageKind.HARNESS_DRAWING:
            pages += _harness_pages(model, record, kinds, sheet)
        elif kind is PageKind.BLOCK_DIAGRAM:
            pages += _diagram_pages(model, record)
        else:
            pages.append(
                SheetPage(
                    key=sheet_key(document, kind, 0),
                    kind=kind,
                    sheet=sheet,
                    fields=_fields(model, record, (PAGE_HEADINGS[kind],)),
                    where=kind.name,
                    group=first_section.name,
                )
            )
    frames = {p.sheet.id: sheet_frame(p.sheet) for p in pages}
    return DocumentSheets(
        sheet=sheet, sizes=sizes_of(model, record), pages=tuple(pages), frames=frozendict(frames)
    )


def document_sheets_of(model: Model) -> frozendict[Id[Document], DocumentSheets]:
    """`document_sheets` of every `Document`, by id: the values render's sheets take."""
    return frozendict({document: document_sheets(model, document) for document in documents(model)})
