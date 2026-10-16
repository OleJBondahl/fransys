"""Whether a document has a content page besides a schematic (pdf-0033), and the list rows."""

from typing import TYPE_CHECKING

from fransys_model.derive import (
    cable_blocks,
    designation_list,
    diagram_sheets,
    document_bom_lines,
    document_scope,
    document_unit,
    harness_cables_for,
)
from fransys_model.vocab import PageKind

from ._drawings import replica_only_sets, schematic_pages
from ._lists import (
    _connector_rows_for_page,
    document_cable_rows,
    plc_channel_rows_for,
    terminal_rows_for,
    wire_rows_for,
)

if TYPE_CHECKING:
    from fransys_model.derive import DocumentRow
    from fransys_model.kernel import Model


_LIST_KINDS = (
    PageKind.PLC_LIST,
    PageKind.TERMINAL_LIST,
    PageKind.CONNECTOR_LIST,
    PageKind.WIRE_LABEL_LIST,
    PageKind.DESIGNATION_LIST,
    PageKind.CABLE_LIST,
    PageKind.BOM,
)


def list_rows(  # noqa: PLR0911 -- one branch per list `PageKind`, as `document._page_source`
    model: Model, record: DocumentRow, kind: PageKind
) -> tuple[object, ...]:
    """The rows `kind`'s list page renders for `record`, for `DOCUMENT_EMPTY_LIST`."""
    if kind is PageKind.PLC_LIST:
        return plc_channel_rows_for(model, record)
    if kind is PageKind.TERMINAL_LIST:
        return tuple(
            row
            for strip in document_scope(model, record.id).strips
            for row in terminal_rows_for(model, record, strip)
        )
    if kind is PageKind.CONNECTOR_LIST:
        return _connector_rows_for_page(model, record)
    if kind is PageKind.WIRE_LABEL_LIST:
        return wire_rows_for(model, record)
    if kind is PageKind.DESIGNATION_LIST:
        return tuple(designation_list(model, unit=document_unit(model, record.id)))
    if kind is PageKind.CABLE_LIST:
        return document_cable_rows(model, record)
    return document_bom_lines(model, record.id)  # kind is PageKind.BOM: the last one


def has_other_content_page(model: Model, record: DocumentRow, pages: tuple[PageKind, ...]) -> bool:
    """A list page with rows, a harness block or a block diagram: what a schematic may yield to."""
    if any(kind in pages and list_rows(model, record, kind) for kind in _LIST_KINDS):
        return True
    cables = harness_cables_for(model, record.id, pages)
    if PageKind.HARNESS_DRAWING in pages and cable_blocks(model, record.id, cables):
        return True
    return PageKind.BLOCK_DIAGRAM in pages and bool(diagram_sheets(model, record.id))


def schematic_yields(model: Model, record: DocumentRow, pages: tuple[PageKind, ...]) -> bool:
    """True when the schematic has no drawing set, is not replica-only, and another page stands."""
    return (
        not schematic_pages(model, record, pages)
        and not replica_only_sets(model, record, pages)
        and has_other_content_page(model, record, pages)
    )
