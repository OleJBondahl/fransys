"""The rows of the sheet index page: one per sheet, block diagram sheets first (SI2, SI3)."""

from fransys_model.kernel import value
from fransys_model.layout import DiagramSheet, Page
lazy from fransys_model.kernel import Model
lazy from fransys_model.vocab import Document, PageKind

from .page_destination import page_destination, sheet_text
from .page_headings import DIAGRAM_TITLE
from .page_titles import page_title_forms
from .sheets import sheets


@value
class SheetIndexRow:
    """One index row: the sheet text (`3`, `2.3`, `B1`), its title forms and its destination label.

    `title` is the longest form and `shorter` the others (`page_title_forms`): the PDF prints
    the first that fits, as the title block does. The page cell is not here: Typst reads the
    physical page at `destination`.
    """

    sheet: str
    title: str
    shorter: tuple[str, ...]
    destination: str


def sheet_index_rows(
    model: Model, record: Document, kinds: tuple[PageKind, ...]
) -> tuple[SheetIndexRow, ...]:
    """One row per sheet of `sheets`; empty for fewer than two sheets (empty-list rule)."""
    found = sheets(model, record, kinds)
    if len(found) < 2:  # noqa: PLR2004 -- SI2: the index prints from two sheets
        return ()
    return tuple(_row(model, one) for one in found)


def _row(model: Model, sheet: DiagramSheet | Page) -> SheetIndexRow:
    forms = (DIAGRAM_TITLE,) if isinstance(sheet, DiagramSheet) else page_title_forms(model, sheet)
    return SheetIndexRow(
        sheet=sheet_text(model, sheet),
        title=forms[0],
        shorter=forms[1:],
        destination=page_destination(model, sheet),
    )
