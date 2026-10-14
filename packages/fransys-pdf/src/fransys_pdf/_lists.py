"""The seven list/BOM pages: tables over model-wide or per-subject derive rows.

The header tuples, the terminal ends labels and the cell text are `fransys_model.derive`'s
own (`derive.rows`), the same objects `fransys_reports.csv` prints from: a root test pins
that neither package keeps a copy of its own.
"""

from typing import TYPE_CHECKING

from fransys_model.derive import (
    BOM_COLUMNS,
    CABLE_LIST_COLUMNS,
    CELL_SEPARATOR,
    CONNECTOR_LABELS,
    DESIGNATION_COLUMNS,
    PIN_COLUMNS,
    PLC_COLUMNS,
    TERMINAL_COLUMNS,
    TERMINAL_LABELS,
    TOP_LEVEL,
    WIRE_COLUMNS,
    boards,
    bom_lines,
    cable_list_rows,
    cell_parts,
    cell_text,
    column_rows,
    connector_items,
    connector_rows,
    connector_rows_of,
    cores_text,
    designation_list,
    document_unit,
    ends_without_jumpers,
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

from ._bridge import BRIDGE_COLUMN_WIDTH_MM, bridge_cell_typst, bridge_geometry, bridge_lane_x_mm
from ._flow import GUTTER_PCT, SHARE_PCT, flow_columns
from ._marks import LIST_HEADING
from ._tables import table_source
from ._typst import description_par, literal

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from fransys_model.derive import (
        ConnectorRow,
        PlcChannelRow,
        TerminalRow,
        TopLevelScope,
        WireRow,
    )
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import AspectNode, Document, Item, Unit


def _humanise(field: str) -> str:
    """`field` as a table header: underscores to spaces, first letter upper-cased."""
    spaced = field.rstrip("_").replace("_", " ")
    return spaced[0].upper() + spaced[1:]


def _cell_typst(value: object) -> str:
    """`value` as one table cell's Typst markup: tuple items in unbreakable boxes (pdf-0013)."""
    match value:
        case tuple():
            parts = cell_parts(value)
            if not parts:
                return f"text({literal('')})"
            return f" + text({literal(CELL_SEPARATOR)}) + ".join(
                f"box(text({literal(part)}))" for part in parts
            )
        case _:
            return f"text({literal(cell_text(value))})"


def _kept_columns(rows: Iterable[tuple[object, ...]], count: int) -> tuple[int, ...]:
    """The indexes of the `count` columns with a non-empty `cell_text` in some row (pdf-0011)."""
    materialised = list(rows)
    return tuple(i for i in range(count) if any(cell_text(row[i]) for row in materialised))


def _widths(wide: list[bool]) -> list[str]:
    """`1fr` per `True`, else `auto`; the last is `1fr` if none is, to span the page (pdf-0008)."""
    widths = ["1fr" if flag else "auto" for flag in wide]
    if widths and "1fr" not in widths:
        widths[-1] = "1fr"
    return widths


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


# -- the Bridge column (pdf-0007) --------------------------------------------------

_TERMINAL_DATA = TERMINAL_COLUMNS[:-1]  # designation, group, index, internal_ends, external_ends
_TERMINAL_SIDES = ("internal_ends", "external_ends")  # both unbounded text: `1fr` each (pdf-0008)


def _terminal_table(
    model: Model,
    rows: tuple[TerminalRow, ...],
    headings: tuple[str, str] = (
        TERMINAL_LABELS["internal_ends"],
        TERMINAL_LABELS["external_ends"],
    ),
    *,
    title: str = "",
    label: str = "",
) -> str:
    """The TERMINAL_LIST table: data columns, then a drawn Bridge column (pdf-0007, 0008, 0011)."""
    if not rows:
        return ""
    geometry = bridge_geometry(tuple(row.jumper_group for row in rows))
    side_label = {"internal_ends": headings[0], "external_ends": headings[1]}
    values = []
    for row in rows:
        ends = dict(
            zip(("internal_ends", "external_ends"), ends_without_jumpers(model, row), strict=True)
        )
        values.append(tuple(ends.get(name, getattr(row, name)) for name in _TERMINAL_DATA))
    kept = _kept_columns(values, len(_TERMINAL_DATA))  # empty columns are not drawn (pdf-0011)
    bridge = any(geometry)  # a strip with no jumper group has an all-empty Bridge column
    if not kept and not bridge:
        return ""
    headers = [side_label.get(_TERMINAL_DATA[i]) or _humanise(_TERMINAL_DATA[i]) for i in kept] + (
        ["Bridge"] if bridge else []
    )
    body = []
    for row_values, row_marks in zip(values, geometry, strict=True):
        cells = [_cell_typst(row_values[i]) for i in kept]
        if bridge:
            cells.append(bridge_cell_typst(row_marks, bridge_lane_x_mm(len(row_marks))))
        body.append(cells)
    widths = _widths([_TERMINAL_DATA[i] in _TERMINAL_SIDES for i in kept])
    if bridge:
        widths.append(f"{BRIDGE_COLUMN_WIDTH_MM}mm")
    heads = [f"strong(text({literal(h)}))" for h in headers]
    return table_source(widths, heads, body, title=title, label=label)


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


def connector_list_page(model: Model, record: Document) -> str:
    """The CONNECTOR_LIST section: a table per connector, headed by its designation (pdf-0030)."""
    sections = []
    for number, row in enumerate(_connector_rows_for_page(model, record)):
        item = items(model)[functions(model)[row.connector].item]
        sections.append(
            _list_heading(row.designation)
            + description_par(item.description)
            + _table(
                PIN_COLUMNS,
                column_rows(row.pins, PIN_COLUMNS),
                ("net", "ends"),
                title=row.designation,
                label=f"conn{number}",
                labels=CONNECTOR_LABELS,
            )
        )
    return flow_columns(sections, share_pct=SHARE_PCT, gutter_pct=GUTTER_PCT)
