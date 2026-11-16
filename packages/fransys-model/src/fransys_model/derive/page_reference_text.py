"""The page fact and the text a page is named by wherever it is printed, one function (render-0018).

A page's number is its place in its PDF, counted from 1 on the cover (pdf-0054, model-0436, model-0462).
"""

lazy from collections.abc import Collection

from fransys_model.layout import Page, sheet_format_of
from fransys_model.vocab import DocumentPreset, PageKind
from fransys_model.vocab.tables import documents
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.document import Document

from .memo import Memo
lazy from .diagram_sheet_order import diagram_unit
lazy from .document_pages import drawn_pages, ordered_pages
lazy from .document_sets import set_printers
lazy from .document_subject import scope_path, unit_label
lazy from .document_unit import document_unit
lazy from .facts.house_settings import diagram_count_of, frame_form_of, front_count_of, reference_text_of, word
lazy from .frame_labels import cell_labels
lazy from .frame_position import partner_position_text, position_text, row_letter
lazy from .instance_tag import unit_system_designation
lazy from .order import widest_text
lazy from .page_presets import document_page_kinds
lazy from .rows_sheet import DiagramSheet

__all__ = ["covered_documents", "far_prefix", "front_pages", "page_reference_text", "pdf_page", "position_at", "position_room"]


def covered_documents(model: Model) -> tuple[Id[Document], ...]:
    """The documents that keep a cover: the ones whose front matter Typst counts and the facade stores."""
    return tuple(document for document in documents(model) if PageKind.COVER in document_page_kinds(model, document))


def front_pages(model: Model, document: Id[Document]) -> int:
    """The pages before the drawings in `document`'s PDF: Typst's count the facade stored with a cover, else 0."""
    return front_count_of(model, document) if document in covered_documents(model) else 0


def _kind_offset(model: Model, document: Id[Document], kind: PageKind) -> int:
    """The pages before the first page of `kind` in `document`'s PDF: the front pages, then the diagram sheets, in kind order.

    A kind the document does not keep is offset by every page of it.
    """
    kinds = document_page_kinds(model, document)
    before = kinds[: kinds.index(kind)] if kind in kinds else kinds
    counts = {PageKind.COVER: front_pages(model, document), PageKind.BLOCK_DIAGRAM: diagram_count_of(model, document)}
    return sum(counts.get(one, 0) for one in before)


def _places(model: Model) -> dict[Id[Page], int]:
    """Each drawn page's number in its PDF: its kind's offset plus its place among the document's drawn pages.

    A page no document prints (it already carries a warning) is counted among all pages, with no front.
    """
    found: dict[Id[Page], int] = {}
    for document in documents(model):
        offset = _kind_offset(model, document, PageKind.SCHEMATIC)
        found.update({page.id: offset + place for place, page in enumerate(drawn_pages(model, document), 1)})
    loose = (page for page in ordered_pages(model) if page.id not in found)
    found.update({page.id: place for place, page in enumerate(loose, 1)})
    return found


_places_of = Memo(_places)


def _diagram_document(model: Model, sheet: DiagramSheet) -> Id[Document] | None:
    """The first document that reads `sheet`: the SYSTEM one for the absolute reading, else its unit's."""
    unit = diagram_unit(sheet)
    for record in documents(model).values():
        if PageKind.BLOCK_DIAGRAM not in document_page_kinds(model, record.id):
            continue
        own = record.preset is DocumentPreset.SYSTEM if unit is None else document_unit(model, record.id) == unit
        if own:
            return record.id
    return None


def pdf_page(model: Model, sheet: Page | DiagramSheet) -> int:
    """The number `sheet` prints: its place in the PDF of the document that prints it, the cover being 1.

    A diagram sheet is its reading's number after the front pages; a drawing page is its place among
    its document's drawn pages. A SYSTEM document's diagram sheets come before its harness pages.
    """
    if isinstance(sheet, DiagramSheet):
        document = _diagram_document(model, sheet)
        return sheet.number if document is None else _kind_offset(model, document, PageKind.BLOCK_DIAGRAM) + sheet.number
    return _places_of(model)[sheet.id]


def page_reference_text(model: Model, page: Page | DiagramSheet) -> str:
    """`p3`: the page named alone, the text of a destination and of a finding about a whole page."""
    return position_text(reference_text_of(model), pdf_page(model, page), None)


def document_prefix(model: Model, document: Id[Document]) -> str:
    """The code that leads a position in `document`, read from another PDF: the one home of that prefix.

    A unit document's code is its unit's designation (`-A2`, nested `-R1-A2`; the unit's title when it is untagged),
    the system document's is the `[words]` entry `system_document_code`, any other document's is its `scope_path`.
    """
    record = documents(model)[document]
    unit = document_unit(model, document)
    if unit is not None:
        return unit_system_designation(model, unit) or unit_label(model, unit)
    if record.location is None and record.item is None:
        return word(model, "system_document_code")
    return scope_path(model, document)


def far_prefix(model: Model, own: Page, partner: Page) -> str:
    """The `document_prefix` of the document printing `partner`, `""` when it is the one printing `own` (or none prints it)."""
    printers = set_printers(model)
    far = printers.get(partner.drawing_set)
    return "" if far is None or far == printers.get(own.drawing_set) else document_prefix(model, far)


def position_at(model: Model, own_page: Page, partner_page: Page, column: int, row: str) -> str:
    """The printed position of frame cell (`column`, `row letter`) on `partner_page`, as a reader of `own_page` sees it.

    The cell alone on the same page, `p<n>:<cell>` in the same PDF, and the far document's unit text
    first across PDFs. It is the one place a partner's position is printed; a reference marker and a
    copied terminal's where-text both call it. Compare a drawn text with this value by recomputing it,
    never by parsing the printed text.
    """
    rows = sheet_format_of(model, partner_page.sheet_format).frame_rows
    labels = cell_labels(frame_form_of(model), rows, column, row)
    pages = (pdf_page(model, own_page), pdf_page(model, partner_page))
    return partner_position_text(reference_text_of(model), *pages, labels, far_prefix(model, own_page, partner_page))


def position_room(model: Model, digits: int, frame: tuple[int, int], digit: str, *, far: Collection[Id[Document]]) -> str:
    """The widest text `position_at` can print before the pages exist: `digits` page digits and the highest `frame` cell, every one `digit`.

    `far` holds the documents that may print a placement in another PDF; empty is the same-PDF text.
    It builds through `partner_position_text` and `document_prefix`, as `position_at` does. Layout sizes a where-text with it.
    """
    columns, rows = frame
    labels = cell_labels(frame_form_of(model), rows, int(digit * len(str(columns))), row_letter(rows - 1))
    refs = reference_text_of(model)
    page = int(digit * digits)
    return widest_text(partner_position_text(refs, 0, page, labels, prefix) for prefix in [document_prefix(model, d) for d in far] or [""])
