"""The sheets a document prints, in order: block diagram sheets, then schematic pages (SI2).

One list for the index's "two or more" and for the outline. The PDF's own page numbers
stay with Typst.
"""

from fransys_model.layout import DiagramSheet, Page, layout_of
from fransys_model.vocab import DocumentPreset, PageKind
lazy from fransys_model.kernel import Model
lazy from fransys_model.vocab import Document

from .diagram_sheet_order import diagram_sheet_order_key
from .document_pages import drawn_pages
from .document_unit import document_unit

__all__ = ["diagram_sheets", "sheets"]


def diagram_sheets(model: Model, record: Document) -> tuple[DiagramSheet, ...]:
    """The diagram sheets of the document's reading, by number: SYSTEM's absolute or its unit's."""
    if record.preset is DocumentPreset.SYSTEM:
        unit = None
    elif (unit := document_unit(model, record)) is None:
        return ()
    found = (sheet for sheet in layout_of(model, DiagramSheet).values() if sheet.unit == unit)
    return tuple(sorted(found, key=diagram_sheet_order_key))


def sheets(
    model: Model, record: Document, kinds: tuple[PageKind, ...]
) -> tuple[DiagramSheet | Page, ...]:
    """Block diagram sheets in number order, then schematic pages in set then page order.

    `kinds` is the document's page kinds: a dropped kind contributes no sheet.
    """
    diagrams = diagram_sheets(model, record) if PageKind.BLOCK_DIAGRAM in kinds else ()
    pages = drawn_pages(model, record) if PageKind.SCHEMATIC in kinds else ()
    return (*diagrams, *pages)
