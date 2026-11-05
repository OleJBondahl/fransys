"""The seven list/BOM pages: tables over model-wide or per-subject derive rows.

The column lists, the column headings and the cell text are `fransys_model.derive`'s own, the
same ones `fransys_reports.csv` prints from.
"""

from typing import TYPE_CHECKING

from fransys_model.derive import (
    cable_list_rows_of,
    column_rows,
    connector_item,
    connector_rows,
    connector_rows_of,
    continued_heading,
    cores_text,
    designation_list,
    document_bom_lines,
    document_scope,
    document_unit,
    is_own_unit_root,
    item_description,
    list_columns,
    list_context,
    list_pdf_columns,
    list_pdf_heading,
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
from ._sizes import rule_of
from ._tables import table_source
from ._typst import description_par, literal

if TYPE_CHECKING:
    from fransys_model.derive import (
        AspectNodeId,
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

    from ._doc import BridgeInputs


def _carried(model: Model, title: str) -> str:
    """The heading a carried table repeats; none for a table with no title."""
    return continued_heading(model, title) if title else ""


_WIDE = {  # per list, the free-text columns (`1fr`, pdf-0008): `auto` ones would starve a `1fr`
    "plc": ("wired_to", "signal_name"),
    "wires": ("from_", "to", "ends"),  # pdf-0027
    "designations": ("description",),
    "connectors": ("net", "ends"),
    "cables": ("description", "from_label", "to_label"),
    "bom": ("description", "designations"),
}


def _table(
    model: Model,
    name: str,
    headers: tuple[str, ...],
    rows: list[tuple[object, ...]],
    heading: tuple[str, str] = ("", ""),
) -> str:
    """The list table: `""` if no rows or all blank (pdf-0019, 0011); `_WIDE` columns: `1fr`.

    `name` is the list whose headings the columns take; `heading` is the `(title, anchor)` of
    a carried table: the heading it repeats and its anchor (pdf-0027).
    """
    if not rows:
        return ""
    kept = _kept_columns(rows, len(headers))
    if not kept:
        return ""
    names = [f"strong(text({literal(list_pdf_heading(model, name, headers[i]))}))" for i in kept]
    body = [[_cell_typst(row[i]) for i in kept] for row in rows]
    widths = _widths([headers[i] in _WIDE[name] for i in kept])
    return table_source(widths, names, body, rule=rule_of(model), heading=heading)


def plc_channel_rows_for(model: Model, record: DocumentRow) -> tuple[PlcChannelRow, ...]:
    """The PLC_LIST rows of `record`'s unit, ends in its location's context (none: full paths)."""
    return plc_channel_rows(model, unit=document_unit(model, record.id), context=record.location)


def plc_list_page(model: Model, record: DocumentRow, *, share_pct: float, gutter_pct: float) -> str:
    """The PLC_LIST: a headed table per `plc_tables` entry in two columns, scoped to the unit."""
    unit = document_unit(model, record.id)
    sections = []
    for number, table in enumerate(plc_tables(model, unit=unit, context=record.location)):
        title = _list_title(model, table.item, unit, table.designation)
        rows: list[tuple[object, ...]] = list(plc_list_rows(model, table.rows))
        sections.append(
            _list_heading(title)
            + _table(
                model,
                "plc",
                list_columns(model, "plc"),
                rows,
                (_carried(model, title), f"plc{number}"),
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


def connector_rows_for(model: Model, record: DocumentRow, board: ItemId) -> tuple[ConnectorRow, ...]:
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


def wire_label_list_page(model: Model, record: DocumentRow, *, share_pct: float, gutter_pct: float) -> str:
    """The WIRE_LABEL_LIST table: every `wire`-faceted conductor, scoped to the unit."""
    wires = list_columns(model, "wires")
    table = _table(
        model,
        "wires",
        wires,
        column_rows(wire_rows_for(model, record), wires),
    )
    return flow_columns([table], share_pct=share_pct, gutter_pct=gutter_pct)


def designation_list_page(model: Model, record: DocumentRow, *, share_pct: float, gutter_pct: float) -> str:
    """The DESIGNATION_LIST table: every item's designation, scoped to the unit."""
    name = "designations"
    designations = list_columns(model, name)
    table = _table(
        model,
        name,
        designations,
        column_rows(designation_list(model, unit=document_unit(model, record.id)), designations),
    )
    return flow_columns([table], share_pct=share_pct, gutter_pct=gutter_pct)


def document_cable_rows(model: Model, record: DocumentRow) -> tuple[CableListRow, ...]:
    """The cable list's rows: the cables the document's drawings draw, `scope.cables` (pdf-0042)."""
    scope = document_scope(model, record.id)
    return cable_list_rows_of(model, {cable.cable for cable in scope.cables})


def cable_list_page(model: Model, record: DocumentRow) -> str:
    """The CABLE_LIST table: one row per cable the document's drawings draw (pdf-0042)."""
    columns = list_pdf_columns(model, "cables")
    rows = [
        tuple(cores_text(row.core_count, row.pairs) if n == "core_count" else getattr(row, n) for n in columns)
        for row in document_cable_rows(model, record)
    ]
    return _table(model, "cables", columns, rows)


def bom_page(model: Model, record: DocumentRow) -> str:
    """The BOM table, scoped by `DocumentScope.bom_scope`."""
    bom = list_columns(model, "bom")
    rows = column_rows(document_bom_lines(model, record.id), bom)
    return _table(model, "bom", bom, rows)


def _list_title(model: Model, item: ItemId, unit: UnitId | None, designation: str | None = None) -> str:
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
    bridge_inputs: BridgeInputs,
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
                (_carried(model, title), f"term{number}"),
                bridge_inputs,
            )
        )
    return flow_columns(sections, share_pct=share_pct, gutter_pct=gutter_pct)


def _connector_rows_for_page(model: Model, record: DocumentRow) -> tuple[ConnectorRow, ...]:
    """The CONNECTOR_LIST rows: a board document's board, else a unit's own, else the location's."""
    scope = document_scope(model, record.id)
    if record.item is not None:
        return tuple(row for board in scope.boards for row in connector_rows_for(model, record, board))
    return connector_rows_of(model, scope.connector_items, unit=scope.unit, context=record.location)


def _connector_section(model: Model, row: ConnectorRow, description: str, number: int) -> str:
    """One connector: heading and table, or with no wired pin its description and one line."""
    if not any(pin.ends or pin.net is not None for pin in row.pins):  # a wire or a net is wired
        return description_par(description) + (f"#par(text({literal(f'{row.designation}: no pin wired')}))\n")
    pins = list_pdf_columns(model, "connectors")
    return (
        _list_heading(row.designation)
        + description_par(description)
        + _table(
            model,
            "connectors",
            pins,
            column_rows(row.pins, pins),
            (_carried(model, row.designation), f"conn{number}"),
        )
    )


def connector_list_page(model: Model, record: DocumentRow, *, share_pct: float, gutter_pct: float) -> str:
    """The CONNECTOR_LIST section: a table per connector, headed by its designation (pdf-0030)."""
    sections = [
        _connector_section(model, row, item_description(model, connector_item(model, row.connector)), n)
        for n, row in enumerate(_connector_rows_for_page(model, record))
    ]
    return flow_columns(sections, share_pct=share_pct, gutter_pct=gutter_pct)
