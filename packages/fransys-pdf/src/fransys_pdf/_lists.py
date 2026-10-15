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
    TOP_LEVEL,
    WIRE_COLUMNS,
    boards,
    bom_lines,
    cable_list_rows,
    column_rows,
    connector_items,
    connector_rows,
    connector_rows_of,
    cores_text,
    designation_list,
    document_unit,
    is_own_unit_root,
    items_at,
    list_context,
    plc_channel_rows,
    plc_list_rows,
    plc_tables,
    printed_designation,
    strip_side_headings,
    terminal_rows,
    terminal_strips,
    unit_connector_items,
    unit_strips,
    wire_rows,
)
from fransys_model.vocab import (
    DocumentPreset,
    functions,
    items,
)

from ._flow import GUTTER_PCT, SHARE_PCT, flow_columns
from ._lists_cells import _cell_typst, _humanise, _kept_columns, _widths
from ._lists_terminal import _terminal_table
from ._marks import LIST_HEADING
from ._tables import table_source
from ._typst import description_par, literal

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_model.derive import (
        ConnectorRow,
        PlcChannelRow,
        TerminalRow,
        TopLevelScope,
        WireRow,
    )
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import AspectNode, Document, Item, Unit


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

    `title` is the heading a carried table repeats with " (cont.)", `label` its anchor (pdf-0027),
    `labels` the header text of a column whose field name reads badly (pdf-0030).
    """
    if not rows:
        return ""
    kept = _kept_columns(rows, len(headers))
    if not kept:
        return ""
    shown = labels or {}
    names = [
        f"strong(text({literal(shown.get(headers[i]) or _humanise(headers[i]))}))" for i in kept
    ]
    body = [[_cell_typst(row[i]) for i in kept] for row in rows]
    widths = _widths([headers[i] in wide for i in kept])
    return table_source(widths, names, body, title=title, label=label)


def plc_channel_rows_for(model: Model, record: Document) -> tuple[PlcChannelRow, ...]:
    """The PLC_LIST rows of `record`'s unit, ends in its location's context (none: full paths)."""
    return plc_channel_rows(model, unit=document_unit(model, record), context=record.location)


def plc_list_page(model: Model, record: Document) -> str:
    """The PLC_LIST: a headed table per `plc_tables` entry in two columns, scoped to the unit."""
    unit = document_unit(model, record)
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
    return flow_columns(sections, share_pct=SHARE_PCT, gutter_pct=GUTTER_PCT)


def _list_context(model: Model, record: Document, subject: Id[Item]) -> Id[AspectNode] | None:
    """The location a list's ends print short against (model-0054 s4, `derive.list_context`)."""
    return list_context(model, subject, location=record.location)


def terminal_rows_for(model: Model, record: Document, strip: Id[Item]) -> tuple[TerminalRow, ...]:
    """`strip`'s `terminal_rows`, printed in `record`'s context (`_list_context`)."""
    return terminal_rows(
        model, strip, unit=document_unit(model, record), context=_list_context(model, record, strip)
    )


def connector_rows_for(model: Model, record: Document, board: Id[Item]) -> tuple[ConnectorRow, ...]:
    """`board`'s `connector_rows`, printed in `record`'s context (`_list_context`)."""
    return connector_rows(
        model, board, unit=document_unit(model, record), context=_list_context(model, record, board)
    )


def wire_rows_for(model: Model, record: Document) -> tuple[WireRow, ...]:
    """The WIRE_LABEL_LIST rows of `record`'s unit, ends printed in its location's context."""
    return wire_rows(model, unit=document_unit(model, record), context=record.location)


def wire_label_list_page(model: Model, record: Document) -> str:
    """The WIRE_LABEL_LIST table: every `wire`-faceted conductor, scoped to the unit."""
    table = _table(
        WIRE_COLUMNS,
        column_rows(wire_rows_for(model, record), WIRE_COLUMNS),
        ("from_", "to", "label"),  # every free-text column: `auto` ones starve a `1fr` (pdf-0027)
    )
    return flow_columns([table], share_pct=SHARE_PCT, gutter_pct=GUTTER_PCT)


def designation_list_page(model: Model, record: Document) -> str:
    """The DESIGNATION_LIST table: every item's designation, scoped to the unit."""
    table = _table(
        DESIGNATION_COLUMNS,
        column_rows(
            designation_list(model, unit=document_unit(model, record)), DESIGNATION_COLUMNS
        ),
        ("description",),
    )
    return flow_columns([table], share_pct=SHARE_PCT, gutter_pct=GUTTER_PCT)


def cable_list_page(model: Model, record: Document) -> str:
    """The CABLE_LIST table: one row per cable of the document's unit; top-level for the system."""
    columns = tuple(name for name in CABLE_LIST_COLUMNS if name != "pairs")
    rows = [
        tuple(
            cores_text(row.core_count, row.pairs) if n == "core_count" else getattr(row, n)
            for n in columns
        )
        for row in cable_list_rows(model, unit=document_unit(model, record))
    ]
    return _table(columns, rows, ("description", "from_label", "to_label"))


def _bom_scope(
    model: Model, record: Document
) -> Id[Item] | Id[AspectNode] | Id[Unit] | TopLevelScope | None:
    """The BOM scope: the unit, else `TOP_LEVEL` for `SYSTEM`, else location or item."""
    unit = document_unit(model, record)
    if unit is not None:
        return unit
    if record.preset is DocumentPreset.SYSTEM:
        return TOP_LEVEL
    return record.location if record.location is not None else record.item


def bom_page(model: Model, record: Document) -> str:
    """The BOM table, scoped by `_bom_scope`."""
    rows = column_rows(bom_lines(model, scope=_bom_scope(model, record)), BOM_COLUMNS)
    return _table(BOM_COLUMNS, rows, ("description", "designations"))


def _terminal_strips_for(model: Model, record: Document) -> tuple[Id[Item], ...]:
    """The TERMINAL_LIST strips: a unit's own, never a nested unit's, else the location's."""
    if (unit := document_unit(model, record)) is not None:
        return unit_strips(model, unit)
    if record.location is None:
        return ()
    at_location = set(items_at(model, record.location))
    return tuple(strip for strip in terminal_strips(model) if strip in at_location)


def _list_title(
    model: Model, item: Id[Item], unit: Id[Unit] | None, designation: str | None = None
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


def terminal_list_page(model: Model, record: Document) -> str:
    """The TERMINAL_LIST section: a headed table per strip; unit-relative (pdf-0012)."""
    unit = document_unit(model, record)
    sections = []
    for number, strip in enumerate(_terminal_strips_for(model, record)):
        if not (rows := terminal_rows_for(model, record, strip)):  # no rows, no page
            continue
        title = _list_title(model, strip, unit)
        sections.append(
            _list_heading(title)
            + description_par(items(model)[strip].description)  # author-0013
            + _terminal_table(
                model, rows, strip_side_headings(model, strip), title=title, label=f"term{number}"
            )
        )
    return flow_columns(sections, share_pct=SHARE_PCT, gutter_pct=GUTTER_PCT)


def _connector_rows_for_page(model: Model, record: Document) -> tuple[ConnectorRow, ...]:
    """The CONNECTOR_LIST rows: a board document's board, else a unit's own, else the location's."""
    unit = document_unit(model, record)
    if record.item is not None:
        return (
            connector_rows_for(model, record, record.item) if record.item in boards(model) else ()
        )
    if unit is not None:
        scope = unit_connector_items(model, unit)
    elif record.location is not None:
        at_location = set(items_at(model, record.location))
        scope = tuple(item for item in connector_items(model) if item in at_location)
    else:
        return ()
    return connector_rows_of(model, scope, unit=unit, context=record.location)


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


def connector_list_page(model: Model, record: Document) -> str:
    """The CONNECTOR_LIST section: a table per connector, headed by its designation (pdf-0030)."""
    sections = [
        _connector_section(row, items(model)[functions(model)[row.connector].item].description, n)
        for n, row in enumerate(_connector_rows_for_page(model, record))
    ]
    return flow_columns(sections, share_pct=SHARE_PCT, gutter_pct=GUTTER_PCT)
