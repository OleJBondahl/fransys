"""Whether a document has a content page besides a schematic (pdf-0033), and the list rows."""

from typing import TYPE_CHECKING, cast

from fransys_model.derive import (
    ListKey,
    PageForm,
    cable_blocks,
    designation_list,
    diagram_sheets,
    document_bom_lines,
    document_scope,
    document_unit,
    harness_cables_for,
    page_preset,
)

from ._drawings import replica_only_sets, schematic_pages
from ._forms import has_form, list_pages
from ._lists import (
    _connector_rows_for_page,
    document_cable_rows,
    plc_channel_rows_for,
    terminal_rows_for,
    wire_rows_for,
)

if TYPE_CHECKING:
    from fransys_model.derive import DiagramSheet, DocumentRow
    from fransys_model.kernel import Model
    from fransys_model.vocab import PageKind


def _terminal_rows(model: Model, record: DocumentRow) -> tuple[object, ...]:
    return tuple(row for strip in document_scope(model, record.id).strips for row in terminal_rows_for(model, record, strip))


def _designation_rows(model: Model, record: DocumentRow) -> tuple[object, ...]:
    return tuple(designation_list(model, unit=document_unit(model, record.id)))


def _bom_rows(model: Model, record: DocumentRow) -> tuple[object, ...]:
    return document_bom_lines(model, record.id)


def list_rows(model: Model, record: DocumentRow, kind: PageKind) -> tuple[object, ...]:
    """The rows `kind`'s list page renders for `record`, for `DOCUMENT_EMPTY_LIST`."""
    rows = {
        ListKey.PLC: plc_channel_rows_for,
        ListKey.TERMINAL: _terminal_rows,
        ListKey.CONNECTOR: _connector_rows_for_page,
        ListKey.WIRE_LABEL: wire_rows_for,
        ListKey.DESIGNATION: _designation_rows,
        ListKey.CABLE: document_cable_rows,
        ListKey.BOM: _bom_rows,
    }
    return rows[cast("ListKey", page_preset(kind).list_key)](model, record)


def has_other_content_page(
    model: Model,
    record: DocumentRow,
    pages: tuple[PageKind, ...],
    diagrams: tuple[DiagramSheet, ...],
) -> bool:
    """A list page with rows, a harness block or a block diagram: what a schematic may yield to."""
    if any(list_rows(model, record, kind) for kind in list_pages(pages)):
        return True
    cables = harness_cables_for(model, record.id, pages)
    if has_form(pages, PageForm.HARNESS_DRAWING) and cable_blocks(model, record.id, cables):
        return True
    return has_form(pages, PageForm.BLOCK_DIAGRAM) and bool(diagram_sheets(model, record.id, diagrams))


def schematic_yields(
    model: Model,
    record: DocumentRow,
    pages: tuple[PageKind, ...],
    diagrams: tuple[DiagramSheet, ...],
) -> bool:
    """True when the schematic has no drawing set, is not replica-only, and another page stands."""
    return (
        not schematic_pages(model, record, pages)
        and not replica_only_sets(model, record, pages)
        and has_other_content_page(model, record, pages, diagrams)
    )
