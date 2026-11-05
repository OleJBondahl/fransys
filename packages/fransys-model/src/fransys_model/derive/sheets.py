"""The sheets a document prints, in order: block diagram sheets, then schematic pages (SI2).

One list for the index's "two or more" and for the outline. The PDF's own page numbers
stay with Typst.
"""

from fransys_model.vocab import DocumentPreset, PageKind
from fransys_model.vocab.tables import documents
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.layout import Page
lazy from fransys_model.vocab import Document

from .diagram_sheet_order import diagram_sheet_order_key
from .document_pages import drawn_pages
from .document_unit import document_unit
lazy from .rows_sheet import DiagramSheet

__all__ = ["diagram_sheets", "sheets"]


def diagram_sheets(model: Model, document: Id[Document], diagrams: tuple[DiagramSheet, ...]) -> tuple[DiagramSheet, ...]:
    """The `diagrams` of the document's reading, by number: SYSTEM's absolute or its unit's.

    `document` is the document's id; `diagrams` are every sheet the diagram engine placed.
    """
    record = documents(model)[document]
    if record.preset is DocumentPreset.SYSTEM:
        unit = None
    elif (unit := document_unit(model, document)) is None:
        return ()
    return tuple(sorted((d for d in diagrams if d.unit == unit), key=diagram_sheet_order_key))


def sheets(
    model: Model,
    document: Id[Document],
    kinds: tuple[PageKind, ...],
    diagrams: tuple[DiagramSheet, ...],
) -> tuple[DiagramSheet | Page, ...]:
    """Block diagram sheets in number order, then schematic pages in set then page order.

    `kinds` is the document's page kinds: a dropped kind contributes no sheet.
    """
    found = diagram_sheets(model, document, diagrams) if PageKind.BLOCK_DIAGRAM in kinds else ()
    pages = drawn_pages(model, document) if PageKind.SCHEMATIC in kinds else ()
    return (*found, *pages)
