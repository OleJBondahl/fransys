"""The seven list/BOM pages: tables over model-wide or per-subject derive rows.

The header tuples, the terminal ends labels and the cell text are `fransys_model.derive`'s
own (`derive.rows`), the same objects `fransys_reports.csv` prints from: a root test pins
that neither package keeps a copy of its own.
"""

from typing import TYPE_CHECKING

from fransys_model.derive import (
    BOM_COLUMNS,
    CABLE_LIST_COLUMNS,
    CONNECTOR_LABELS,
    DESIGNATION_COLUMNS,
    PIN_COLUMNS,
    PLC_COLUMNS,
    WIRE_COLUMNS,
    cable_list_rows_of,
    column_label,
    column_rows,
    connector_item,
    connector_rows,
    connector_rows_of,
    cores_text,
    designation_list,
    document_bom_lines,
    document_scope,
    document_unit,
    is_own_unit_root,
    item_description,
    list_context,
    plc_channel_rows,
    plc_list_rows,
    plc_tables,
    printed_designation,
    strip_side_headings,
    terminal_rows,
    wire_rows,
)

from ._flow import flow_columns
from ._lists_cells import _cell_typst, _kept_columns, _widths
from ._lists_terminal import _terminal_table
from ._marks import LIST_HEADING
from ._tables import table_source
from ._typst import description_par, literal

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_model.derive import (
        AspectNodeId,
        BridgePieceRow,
        CableListRow,
        ConnectorRow,
        DocumentRow,
        ItemId,
        PlcChannelRow,
        TerminalRow,
        UnitId,
        WireRow,
    )
    from fransys_model.kernel import Model


def _table(  # noqa: PLR0913 -- the list, its wide columns, its heading, anchor and labels
    headers: tuple[str, ...],
    rows: list[tuple[object, ...]],
    wide: tuple[str, ...],
    *,
    title: str = "",
    label: str = "",
    labels: Mapping[str, str] | None = None,
) -> str:
    """The list table: `""` if no rows or all blank (pdf-0019, 0011); `wide`: `1fr` (0008).

    `title` is the heading a carried table repeats, `label` its anchor (pdf-0027),
    `labels` the header text of a column whose field name reads badly (pdf-0030).
    """
    if not rows:
        return ""
    kept = _kept_columns(rows, len(headers))
    if not kept:
        return ""
    shown = labels or {}
    names = [
        f"strong(text({literal(shown.get(headers[i]) or column_label(headers[i]))}))" for i in kept
    ]
    body = [[_cell_typst(row[i]) for i in kept] for row in rows]
    widths = _widths([headers[i] in wide for i in kept])
    return table_source(widths, names, body, title=title, label=label)


def plc_channel_rows_for(model: Model, record: DocumentRow) -> tuple[PlcChannelRow, ...]:
    """The PLC_LIST rows of `record`'s unit, ends in its location's context (none: full paths)."""
    return plc_channel_rows(model, unit=document_unit(model, record.id), context=record.location)


def plc_list_page(model: Model, record: DocumentRow, *, share_pct: float, gutter_pct: float) -> str:
    """The PLC_LIST: a headed table per `plc_tables` entry in two columns, scoped to the unit."""
    unit = document_unit(model, record.id)
    sections = []
    for number, table in enumerate(plc_tables(model, unit=unit, context=record.location)):
        title = _list_title(model, table.item, unit, table.designation)
        rows: list[tuple[object, ...]] = list(plc_list_rows(table.rows))
        sections.append(
            _list_heading(title)
            + _table(
                PLC_COLUMNS, rows, ("wired_to", "signal_name"), title=title, label=f"plc{number}"
            )
        )
    return flow_columns(sections, share_pct=share_pct, gutter_pct=gutter_pct)


def _list_context(model: Model, record: DocumentRow, subject: ItemId) -> AspectNodeId | None:
    """The location a list's ends print short against (model-0054 s4, `derive.list_context`)."""
    return list_context(model, subject, location=record.location)


def terminal_rows_for(model: Model, record: DocumentRow, strip: ItemId) -> tuple[TerminalRow, ...]:
    """`strip`'s `terminal_rows`, printed in `record`'s context (`_list_context`)."""
    return terminal_rows(
        model,
        strip,
        unit=document_unit(model, record.id),
        context=_list_context(model, record, strip),
    )


def connector_rows_for(
    model: Model, record: DocumentRow, board: ItemId
) -> tuple[ConnectorRow, ...]:
    """`board`'s `connector_rows`, printed in `record`'s context (`_list_context`)."""
    return connector_rows(
        model,
        board,
        unit=document_unit(model, record.id),
        context=_list_context(model, record, board),
    )


def wire_rows_for(model: Model, record: DocumentRow) -> tuple[WireRow, ...]:
    """The WIRE_LABEL_LIST rows of `record`'s unit, ends printed in its location's context."""
    return wire_rows(model, unit=document_unit(model, record.id), context=record.location)


def wire_label_list_page(
    model: Model, record: DocumentRow, *, share_pct: float, gutter_pct: float
) -> str:
    """The WIRE_LABEL_LIST table: every `wire`-faceted conductor, scoped to the unit."""
    table = _table(
        WIRE_COLUMNS,
        column_rows(wire_rows_for(model, record), WIRE_COLUMNS),
        ("from_", "to", "label"),  # every free-text column: `auto` ones starve a `1fr` (pdf-0027)
    )
    return flow_columns([table], share_pct=share_pct, gutter_pct=gutter_pct)


def designation_list_page(
    model: Model, record: DocumentRow, *, share_pct: float, gutter_pct: float
) -> str:
    """The DESIGNATION_LIST table: every item's designation, scoped to the unit."""
    table = _table(
        DESIGNATION_COLUMNS,
        column_rows(
            designation_list(model, unit=document_unit(model, record.id)), DESIGNATION_COLUMNS
        ),
        ("description",),
    )
    return flow_columns([table], share_pct=share_pct, gutter_pct=gutter_pct)


def document_cable_rows(model: Model, record: DocumentRow) -> tuple[CableListRow, ...]:
    """The cable list's rows: the cables the document's drawings draw, `scope.cables` (pdf-0042)."""
    scope = document_scope(model, record.id)
    return cable_list_rows_of(model, {cable.cable for cable in scope.cables})


def cable_list_page(model: Model, record: DocumentRow) -> str:
    """The CABLE_LIST table: one row per cable the document's drawings draw (pdf-0042)."""
    columns = tuple(name for name in CABLE_LIST_COLUMNS if name != "pairs")
    rows = [
        tuple(
            cores_text(row.core_count, row.pairs) if n == "core_count" else getattr(row, n)
            for n in columns
        )
        for row in document_cable_rows(model, record)
    ]
    return _table(columns, rows, ("description", "from_label", "to_label"))


def bom_page(model: Model, record: DocumentRow) -> str:
    """The BOM table, scoped by `DocumentScope.bom_scope`."""
    rows = column_rows(document_bom_lines(model, record.id), BOM_COLUMNS)
    return _table(BOM_COLUMNS, rows, ("description", "designations"))


def _list_title(
    model: Model, item: ItemId, unit: UnitId | None, designation: str | None = None
) -> str:
    """A section's heading text, unit-relative; `""` for a unit's own root (model-0061).

    `designation` is the printed one when the caller has it (`PlcTable.designation`).
    """
    if is_own_unit_root(model, item, unit):
        return ""
    return printed_designation(model, item, unit=unit) if designation is None else designation


def _list_heading(title: str) -> str:
    """The level-2 heading of `title`, `""` for none."""
    return f"{LIST_HEADING}text({literal(title)}))\n" if title else ""


def terminal_list_page(
    model: Model,
    record: DocumentRow,
    bridges: Mapping[str, BridgePieceRow] | None = None,
    *,
    share_pct: float,
    gutter_pct: float,
) -> str:
    """The TERMINAL_LIST section: a headed table per strip; unit-relative (pdf-0012)."""
    unit = document_unit(model, record.id)
    sections = []
    for number, strip in enumerate(document_scope(model, record.id).strips):
        if not (rows := terminal_rows_for(model, record, strip)):  # no rows, no page
            continue
        title = _list_title(model, strip, unit)
        sections.append(
            _list_heading(title)
            + description_par(item_description(model, strip))  # author-0013
            + _terminal_table(
                model,
                rows,
                strip_side_headings(model, strip),
                title=title,
                label=f"term{number}",
                bridges=bridges,
            )
        )
    return flow_columns(sections, share_pct=share_pct, gutter_pct=gutter_pct)


def _connector_rows_for_page(model: Model, record: DocumentRow) -> tuple[ConnectorRow, ...]:
    """The CONNECTOR_LIST rows: a board document's board, else a unit's own, else the location's."""
    scope = document_scope(model, record.id)
    if record.item is not None:
        return tuple(
            row for board in scope.boards for row in connector_rows_for(model, record, board)
        )
    return connector_rows_of(model, scope.connector_items, unit=scope.unit, context=record.location)


def _connector_section(row: ConnectorRow, description: str, number: int) -> str:
    """One connector: heading and table, or with no wired pin its description and one line."""
    if not any(pin.ends or pin.net is not None for pin in row.pins):  # a wire or a net is wired
        return description_par(description) + (
            f"#par(text({literal(f'{row.designation}: no pin wired')}))\n"
        )
    return (
        _list_heading(row.designation)
        + description_par(description)
        + _table(
            PIN_COLUMNS,
            column_rows(row.pins, PIN_COLUMNS),
            ("net", "ends"),
            title=row.designation,
            label=f"conn{number}",
            labels=CONNECTOR_LABELS,
        )
    )


def connector_list_page(
    model: Model, record: DocumentRow, *, share_pct: float, gutter_pct: float
) -> str:
    """The CONNECTOR_LIST section: a table per connector, headed by its designation (pdf-0030)."""
    sections = [
        _connector_section(row, item_description(model, connector_item(model, row.connector)), n)
        for n, row in enumerate(_connector_rows_for_page(model, record))
    ]
    return flow_columns(sections, share_pct=share_pct, gutter_pct=gutter_pct)
