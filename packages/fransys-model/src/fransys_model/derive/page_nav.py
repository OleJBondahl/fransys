"""What the PDF's links, anchors and outline need from the model (NV2, NV3, PAGES-NAV, PDF-LINKS).

Reached as `fransys_model.derive.page_nav.<name>`, never re-exported from `derive/__init__.py`.
Page numbers and titles come from `pdf_page`, `sheet_title_text` and `page_title`; nothing here
formats them again.
"""

from decimal import Decimal
lazy from collections.abc import Iterable, Mapping

from fransys_model.layout import FrameCell, LinkMarker, Page, layout_of, sheet_format_of
from fransys_model.vocab.tables import documents
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.document import Document

from .document_pages import drawn_pages
from .facts.roles import function_role
from .marker_text import marker_cell, marker_line_targets
from .memo import Memo
from .order import drawn_on_page
from .order_placements import function_placements
from .page_destination import cell_destination, page_destination, sheet_title_text
from .page_headings import diagram_title
from .page_titles import page_title
from .rows_nav import OutlineSheet, PageAnchor, ReferenceLink
from .rows_sheet import DiagramSheet

__all__ = ["OutlineSheet", "PageAnchor", "ReferenceLink", "outline_sheets", "page_anchors", "reference_links", "same_pdf"]


type Boxes = Mapping[Id[LinkMarker], tuple[int, int, int, int]]


def _printed(model: Model) -> dict[Id[Document], frozenset[Id[Page]]]:
    """Each document's drawn pages, by id."""
    return {document: frozenset(page.id for page in drawn_pages(model, document)) for document in documents(model)}


_printed_pages = Memo(_printed)


def same_pdf(model: Model, own_page: Page, target_page: Page, document: Id[Document] | None) -> bool:
    """Whether a reference from `own_page` to `target_page` stays in one PDF: both are drawn pages of `document` (`None`: of one document).

    A target in another document's PDF, or in no PDF, gets no link: its `p<n>` label would name this PDF's page n (PDF-LINKS R3).
    """
    printed = _printed_pages(model)
    return any(own_page.id in ids and target_page.id in ids for doc, ids in printed.items() if document in {None, doc})


def reference_links(model: Model, document: Id[Document], page_id: Id[Page], boxes: Boxes) -> tuple[ReferenceLink, ...]:
    """The links on page `page_id` of `document`'s PDF: one per line of each link marker's `boxes` entry, each `(x, y, width, height)` in G (NV2).

    The facade measures each box from the drawn marker (SY7); this slices it into its printed lines and gives each its
    end's cell on that end's page, even the same page (R2, R3). A line whose end is
    in another PDF, or names no end, has no link.
    """
    pages = layout_of(model, Page)
    page = pages[page_id]
    found = []
    for marker in drawn_on_page(model, LinkMarker, page):
        targets = marker_line_targets(model, marker)
        for box, end in zip(_slices(boxes[marker.id], len(targets)), targets, strict=True):
            if end is not None and same_pdf(model, page, pages[end.page], document):
                cell = _end_cell(model, end)
                (x, y, width, height), target = box, cell_destination(model, pages[end.page], cell)
                found.append(ReferenceLink(x=x, y=y, width=width, height=height, target=target))
    return tuple(found)


def _end_cell(model: Model, end: LinkMarker) -> FrameCell:
    """The frame cell of the marker `end`."""
    column, row = marker_cell(model, end)
    return FrameCell(column=column, row=row)


def _slices(box: tuple[int, int, int, int], count: int) -> list[tuple[int, int, int, int]]:
    """`box` cut into `count` equal strips, top to bottom."""
    x, y, width, height = box
    return [(x, y + height * i // count, width, height * (i + 1) // count - height * i // count) for i in range(count)]


def _target_cells(model: Model, document: Id[Document]) -> dict[Id[Page], dict[FrameCell, None]]:
    """The cells of `document`'s PDF that a link names: a marker line's end, and each placement of a terminal placed twice."""
    pages = layout_of(model, Page)
    found: dict[Id[Page], dict[FrameCell, None]] = {}
    for marker in layout_of(model, LinkMarker).values():
        for end in marker_line_targets(model, marker):
            if end is not None and same_pdf(model, pages[marker.page], pages[end.page], document):
                found.setdefault(end.page, {})[_end_cell(model, end)] = None
    for function, places in function_placements(model).items():
        if len(places) > 1 and function_role(model, function).terminal:
            for page, cell in places:
                if same_pdf(model, pages[page], pages[page], document):
                    found.setdefault(page, {})[cell] = None
    return found


_target_cells_of = Memo(_target_cells)


def page_anchors(model: Model, document: Id[Document], page_id: Id[Page]) -> tuple[PageAnchor, ...]:
    """The destination of every cell on page `page_id` that a link of `document`'s PDF names: its top-left corner in mm (PDF-LINKS R5b)."""
    page = layout_of(model, Page)[page_id]
    sheet = sheet_format_of(model, page.sheet_format)
    column, row = Decimal(sheet.content_width_mm) / sheet.frame_columns, Decimal(sheet.content_height_mm) / sheet.frame_rows
    return tuple(
        PageAnchor(
            label=cell_destination(model, page, cell),
            x=sheet.content_x_mm + column * (cell.column - 1),
            y=sheet.content_y_mm + row * (ord(cell.row) - ord("A")),
        )
        for cell in _target_cells_of(model, document).get(page_id, {})
    )


def outline_sheets(model: Model, sheets: Iterable[Id[Page] | DiagramSheet]) -> tuple[OutlineSheet, ...]:
    """One entry per sheet (a page id or a diagram sheet), in order: "3: Pump 1" (NV3)."""
    out = []
    for given in sheets:
        if isinstance(given, DiagramSheet):
            sheet, title, entries = given, diagram_title(model), ()
        else:
            sheet = layout_of(model, Page)[given]
            title, entries = page_title(model, sheet), ()
        out.append(
            OutlineSheet(
                destination=page_destination(model, sheet),
                title=sheet_title_text(model, sheet, title),
                entries=entries,
            )
        )
    return tuple(out)
