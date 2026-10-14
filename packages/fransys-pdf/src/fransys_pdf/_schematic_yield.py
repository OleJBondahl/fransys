"""Whether a document has a content page besides a schematic (pdf-0033), and the list rows."""

from typing import TYPE_CHECKING

from fransys_model.derive import (
    bom_lines,
    cable_list_rows,
    designation_list,
    diagram_sheets,
    document_unit,
)
from fransys_model.vocab import PageKind

from ._drawings import (
    cable_blocks,
    harness_cables_for,
    replica_only_sets,
    schematic_pages,
)
from ._lists import (
    _bom_scope,
    _connector_rows_for_page,
    _terminal_strips_for,
    plc_channel_rows_for,
    terminal_rows_for,
    wire_rows_for,
)

if TYPE_CHECKING:
    from fransys_model.kernel import Model
    from fransys_model.vocab import Document


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
    model: Model, record: Document, kind: PageKind
) -> tuple[object, ...]:
    """The rows `kind`'s list page renders for `record`, for `DOCUMENT_EMPTY_LIST`."""
    if kind is PageKind.PLC_LIST:
        return plc_channel_rows_for(model, record)
    if kind is PageKind.TERMINAL_LIST:
        return tuple(
            row
            for strip in _terminal_strips_for(model, record)
            for row in terminal_rows_for(model, record, strip)
        )
    if kind is PageKind.CONNECTOR_LIST:
        return _connector_rows_for_page(model, record)
    if kind is PageKind.WIRE_LABEL_LIST:
        return wire_rows_for(model, record)
    if kind is PageKind.DESIGNATION_LIST:
        return tuple(designation_list(model, unit=document_unit(model, record)))
    if kind is PageKind.CABLE_LIST:
        return tuple(cable_list_rows(model, unit=document_unit(model, record)))
    return tuple(
        bom_lines(model, scope=_bom_scope(model, record))
    )  # kind is PageKind.BOM: the last one


def has_other_content_page(model: Model, record: Document, pages: tuple[PageKind, ...]) -> bool:
    """A list page with rows, a harness block or a block diagram: what a schematic may yield to."""
    if any(kind in pages and list_rows(model, record, kind) for kind in _LIST_KINDS):
        return True
    cables = harness_cables_for(model, record, pages)
    if PageKind.HARNESS_DRAWING in pages and cable_blocks(model, record, cables):
        return True
    return PageKind.BLOCK_DIAGRAM in pages and bool(diagram_sheets(model, record))


def schematic_yields(model: Model, record: Document, pages: tuple[PageKind, ...]) -> bool:
    """True when the schematic has no drawing set, is not replica-only, and another page stands."""
    return (
        not schematic_pages(model, record, pages)
        and not replica_only_sets(model, record, pages)
        and has_other_content_page(model, record, pages)
    )
