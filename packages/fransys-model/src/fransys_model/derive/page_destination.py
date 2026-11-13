"""The label of a drawing page's PDF named destination and its outline entry, one fact in one place (OVERVIEW O21).

Both print the page's number in its PDF, `pdf_page` (model-0436), so no label repeats in one PDF.
"""

from collections import defaultdict

from fransys_model.kernel import Id, value
from fransys_model.layout import FrameCell, Page, sheet_format_of
from fransys_model.layout.page_slices import page_members
from fransys_model.vocab.tables import documents, functions
lazy from fransys_model.kernel import Model
lazy from fransys_model.vocab.core import Item

from .document_pages import drawn_pages
from .export_names import document_export_name
from .facts.house_settings import frame_form_of, reference_text_of
from .frame_labels import cell_labels
from .frame_position import position_text
from .page_reference_text import page_reference_text, pdf_page
lazy from .rows_sheet import DiagramSheet

__all__ = ["ItemPage", "cell_destination", "item_pages", "page_destination", "sheet_title_text"]


def page_destination(model: Model, sheet: Page | DiagramSheet) -> str:
    """`p<n>`: the destination label of a page, `n` its place in its PDF."""
    return page_reference_text(model, sheet)


def cell_destination(model: Model, page: Page, cell: FrameCell) -> str:
    """`p3:B2`: the destination label of frame cell `cell` on `page`, the printed form of a position in the same PDF."""
    rows = sheet_format_of(model, page.sheet_format).frame_rows
    labels = cell_labels(frame_form_of(model), rows, cell.column, cell.row)
    return position_text(reference_text_of(model), pdf_page(model, page), labels)


def sheet_title_text(model: Model, sheet: Page | DiagramSheet, title: str) -> str:
    """`3: Pump 1`: a page's outline entry text; with no title, `3`."""
    number = str(pdf_page(model, sheet))
    return f"{number}: {title}" if title else number


@value
class ItemPage:
    """One drawing page that shows an item: the PDF, the page's destination and its text."""

    file: str
    destination: str
    text: str


def item_pages(model: Model) -> dict[Id[Item], tuple[ItemPage, ...]]:
    """Every item with each drawing page of a whole-system write that draws one of its functions.

    The file is the one `write` names the document's PDF; the text is `position_text` of the
    page and the frame cell of the first membership row on it. Empty when the model has no document.
    """
    found: dict[Id[Item], dict[tuple[str, str], ItemPage]] = defaultdict(dict)
    funcs = functions(model)
    refs, frame = reference_text_of(model), frame_form_of(model)
    for record in documents(model).values():
        name = document_export_name(model, None, record)
        for page in drawn_pages(model, record.id):
            rows = sheet_format_of(model, page.sheet_format).frame_rows
            destination = page_destination(model, page)
            for member in page_members(model, page):
                if member.function is None:
                    continue
                column, row = member.cell.column, member.cell.row
                labels = cell_labels(frame, rows, column, row)
                text = position_text(refs, pdf_page(model, page), labels)
                item = funcs[member.function].item
                found[item].setdefault((name, destination), ItemPage(file=name, destination=destination, text=text))
    return {item: tuple(pages.values()) for item, pages in found.items()}
