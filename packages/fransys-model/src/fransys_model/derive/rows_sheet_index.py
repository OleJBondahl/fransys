"""The rows of the sheet index page: one per sheet, block diagram sheets first (SI2, SI3)."""

from fransys_model.kernel import value
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.layout import Page
lazy from fransys_model.vocab import Document, PageKind

from .page_destination import page_destination
from .page_headings import diagram_title
from .page_reference_text import pdf_page
from .page_titles import page_title_forms
from .rows_sheet import DiagramSheet
from .sheets import sheets

_SHEETS = 2  # SI2: the index prints from two sheets


@value
class SheetIndexRow:
    """One index row: its title forms, its destination label and its page (`pdf_page`).

    `title` is the longest form and `shorter` the others (`page_title_forms`): the PDF prints
    the first that fits, as the title block does.
    """

    title: str
    shorter: tuple[str, ...]
    destination: str
    page: int


def sheet_index_rows(
    model: Model,
    document: Id[Document],
    kinds: tuple[PageKind, ...],
    diagrams: tuple[DiagramSheet, ...],
) -> tuple[SheetIndexRow, ...]:
    """One row per sheet of `sheets`; empty for fewer than two sheets (empty-list rule).

    `document` is the document's id; `diagrams` are every sheet the diagram engine placed.
    """
    found = sheets(model, document, kinds, diagrams)
    if len(found) < _SHEETS:
        return ()
    return tuple(_row(model, one) for one in found)


def _row(model: Model, sheet: DiagramSheet | Page) -> SheetIndexRow:
    forms = (diagram_title(model),) if isinstance(sheet, DiagramSheet) else page_title_forms(model, sheet)
    return SheetIndexRow(
        title=forms[0],
        shorter=forms[1:],
        destination=page_destination(model, sheet),
        page=pdf_page(model, sheet),
    )
