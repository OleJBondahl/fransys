"""A document's drawn pages and sheets as plain rows: what `fransys_pdf` reads of the layout.

The pages are the schematic drawing sets' (`drawn_pages`); the sheets are `SheetFormat` records
projected to `SheetRow`, so pdf names no layout type (OUTPUT-DOORS).
"""

from fransys_model.layout import CableBlock, layout_of, sheet_for, sheet_format_of
from fransys_model.vocab import PageKind
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.layout import Page, SheetFormat
lazy from fransys_model.vocab import Document, Unit

from .cable_drawing import cable_block_key
from .document_pages import drawn_pages, is_replica_only_undrawn
from .document_sheets import document_sheet_format
from .printed_sets import document_drawing_sets
from .rows_drawn_sheets import CableBlockSize, ReplicaOnlySet, SheetGroup, SheetRow
from .schematic_subject import has_schematic_subject

__all__ = [
    "cable_block_sizes",
    "document_sheet",
    "kind_sheet",
    "mixed_sheet_groups",
    "replica_only_sets",
    "schematic_page_ids",
]


def _row(sheet: SheetFormat) -> SheetRow:
    return SheetRow(
        width_mm=sheet.width_mm,
        height_mm=sheet.height_mm,
        content_x_mm=sheet.content_x_mm,
        content_y_mm=sheet.content_y_mm,
        content_width_mm=sheet.content_width_mm,
        content_height_mm=sheet.content_height_mm,
        module_mm=sheet.module_mm,
    )


def document_sheet(model: Model, document: Id[Document], pages: tuple[PageKind, ...]) -> SheetRow:
    """The paper of every page of `document`: `document_sheet_format` as a `SheetRow`."""
    return _row(document_sheet_format(model, document, pages))


def kind_sheet(model: Model, kind: PageKind, unit: Id[Unit] | None = None) -> SheetRow:
    """The sheet a page of `kind` of `unit` is on (`layout.sheet_for`) as a `SheetRow`."""
    return _row(sheet_for(model, kind, unit))


def schematic_page_ids(
    model: Model, document: Id[Document], pages: tuple[PageKind, ...]
) -> tuple[Id[Page], ...]:
    """The ids of the SCHEMATIC pages of `document` in set then page order.

    Empty when `pages` has no SCHEMATIC or `document` has no location or unit subject.
    """
    if PageKind.SCHEMATIC not in pages or not has_schematic_subject(model, document):
        return ()
    return tuple(page.id for page in drawn_pages(model, document))


def replica_only_sets(
    model: Model, document: Id[Document], pages: tuple[PageKind, ...]
) -> tuple[ReplicaOnlySet, ...]:
    """The matched drawing sets of `document` that its SCHEMATIC skips as replica-only.

    Empty on the same terms as `schematic_page_ids`.
    """
    if PageKind.SCHEMATIC not in pages or not has_schematic_subject(model, document):
        return ()
    return tuple(
        ReplicaOnlySet(id=found.id, location=found.location)
        for found in document_drawing_sets(model, document)
        if is_replica_only_undrawn(model, found)
    )


def mixed_sheet_groups(
    model: Model, document: Id[Document], pages: tuple[PageKind, ...]
) -> tuple[SheetGroup, ...]:
    """Each sheet format the drawn pages name with its page numbers; empty unless more than one."""
    if PageKind.SCHEMATIC not in pages:
        return ()
    grouped: dict[Id[SheetFormat] | None, list[int]] = {}
    for page in drawn_pages(model, document):
        grouped.setdefault(page.sheet_format, []).append(page.number)
    if len(grouped) <= 1:
        return ()
    return tuple(
        SheetGroup(name=sheet_format_of(model, key).name, numbers=tuple(numbers))
        for key, numbers in grouped.items()
    )


def cable_block_sizes(model: Model) -> dict[str, CableBlockSize]:
    """Each laid-out cable block's size in G and sheet module, by `cable_block_key`."""
    return {
        cable_block_key(found.unit, found.subject): CableBlockSize(
            width=found.width,
            height=found.height,
            module_mm=sheet_format_of(model, found.sheet_format).module_mm,
        )
        for found in layout_of(model, CableBlock).values()
    }
