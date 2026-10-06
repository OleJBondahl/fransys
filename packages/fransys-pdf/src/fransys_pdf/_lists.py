"""The six list/BOM pages: tables over model-wide or per-subject derive rows (spec P9).

The header tuples, the terminal ends labels and the cell text are `fransys_model.derive`'s
own (`derive.rows`), the same objects `fransys_reports.csv` prints from: a root test pins
that neither package keeps a copy of its own.
"""

from dataclasses import dataclass
from itertools import product
from typing import TYPE_CHECKING

from fransys_model.derive import (
    BOM_COLUMNS,
    CABLE_LIST_COLUMNS,
    CELL_SEPARATOR,
    CONNECTOR_COLUMNS,
    DESIGNATION_COLUMNS,
    PIN_COLUMNS,
    PLC_COLUMNS,
    TERMINAL_COLUMNS,
    TERMINAL_LABELS,
    TOP_LEVEL,
    WIRE_COLUMNS,
    boards,
    bom_lines,
    build_indexes,
    cable_list_rows,
    cell_parts,
    cell_text,
    column_rows,
    connector_rows,
    designation_list,
    document_unit,
    is_own_unit_root,
    items_at,
    list_context,
    pin_lines,
    plc_channel_rows,
    printed_designation,
    terminal_items,
    terminal_rows,
    terminal_strips,
    unit_boards,
    unit_strips,
    wire_rows,
)
from fransys_model.vocab import (
    ConductorKind,
    DocumentPreset,
    PortRole,
    conductors,
    items,
    ports,
)

from ._typst import description_par, literal

if TYPE_CHECKING:
    from collections.abc import Iterable

    from fransys_model.derive import (
        ConnectorRow,
        PlcChannelRow,
        TerminalRow,
        TopLevelScope,
        WireRow,
    )
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import AspectNode, Conductor, Document, Item, Unit


def _humanise(field: str) -> str:
    """`field` as a table header: underscores to spaces, first letter upper-cased (spec P9)."""
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


def _table(headers: tuple[str, ...], rows: list[tuple[object, ...]], wide: tuple[str, ...]) -> str:
    """`#table(...)`: `""` if no rows or all blank (pdf-0019, 0011); `wide`: `1fr` (0008)."""
    if not rows:
        return ""
    kept = _kept_columns(rows, len(headers))
    if not kept:
        return ""
    header = (
        "table.header("
        + ", ".join(f"strong(text({literal(_humanise(headers[i]))}))" for i in kept)
        + ")"
    )
    cells = [header]
    for row in rows:
        cells.extend(_cell_typst(row[i]) for i in kept)
    widths = ", ".join(_widths([headers[i] in wide for i in kept]))
    return f"#table(columns: ({widths}), stroke: 0.5pt, " + ", ".join(cells) + ")"


def plc_channel_rows_for(model: Model, record: Document) -> tuple[PlcChannelRow, ...]:
    """The PLC_LIST rows of `record`'s unit, ends in its location's context (none: full paths)."""
    return plc_channel_rows(model, unit=document_unit(model, record), context=record.location)


def plc_list_page(model: Model, record: Document) -> str:
    """The PLC_LIST table: every PLC channel, scoped to the document's unit (spec P9, U6)."""
    return _table(
        PLC_COLUMNS,
        column_rows(plc_channel_rows_for(model, record), PLC_COLUMNS),
        ("wired_to", "signal_name"),
    )


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
    """The WIRE_LABEL_LIST table: every `wire`-faceted conductor, scoped to the unit (P9, U6)."""
    return _table(
        WIRE_COLUMNS,
        column_rows(wire_rows_for(model, record), WIRE_COLUMNS),
        ("label",),
    )


def designation_list_page(model: Model, record: Document) -> str:
    """The DESIGNATION_LIST table: every item's designation, scoped to the unit (P9, U6)."""
    return _table(
        DESIGNATION_COLUMNS,
        column_rows(
            designation_list(model, unit=document_unit(model, record)), DESIGNATION_COLUMNS
        ),
        ("description",),
    )


def cable_list_page(model: Model) -> str:
    """The CABLE_LIST table: one row per top-level cable, model-wide (units spec U3)."""
    return _table(
        CABLE_LIST_COLUMNS,
        column_rows(cable_list_rows(model), CABLE_LIST_COLUMNS),
        ("description", "from_label", "to_label"),
    )


def _bom_scope(
    model: Model, record: Document
) -> Id[Item] | Id[AspectNode] | Id[Unit] | TopLevelScope | None:
    """The BOM scope (U5): the unit, else `TOP_LEVEL` for `SYSTEM`, else location or item."""
    unit = document_unit(model, record)
    if unit is not None:
        return unit
    if record.preset is DocumentPreset.SYSTEM:
        return TOP_LEVEL
    return record.location if record.location is not None else record.item


def bom_page(model: Model, record: Document) -> str:
    """The BOM table, scoped by `_bom_scope` (spec P9, units spec U5)."""
    return _table(
        BOM_COLUMNS,
        column_rows(bom_lines(model, scope=_bom_scope(model, record)), BOM_COLUMNS),
        ("description", "designations"),
    )


def _terminal_strips_for(model: Model, record: Document) -> tuple[Id[Item], ...]:
    """The TERMINAL_LIST strips: a unit's own, never a nested unit's (U6), else the location's."""
    if (unit := document_unit(model, record)) is not None:
        return unit_strips(model, unit)
    if record.location is None:
        return ()
    at_location = set(items_at(model, record.location))
    return tuple(strip for strip in terminal_strips(model) if strip in at_location)


def _list_heading(model: Model, item: Id[Item], unit: Id[Unit] | None) -> str:
    """A section's level-2 heading, unit-relative; `""` for a unit's own root (UNIT-ID I4)."""
    if is_own_unit_root(model, item, unit):
        return ""
    return f"#heading(level: 2, text({literal(printed_designation(model, item, unit=unit))}))\n"


def terminal_list_page(model: Model, record: Document) -> str:
    """The TERMINAL_LIST section: a headed table per strip (P9); unit-relative (pdf-0012)."""
    sections = [
        _list_heading(model, strip, document_unit(model, record))
        + description_par(items(model)[strip].description)  # author-0013
        + _terminal_table(model, rows, _side_headings(model, strip))
        for strip in _terminal_strips_for(model, record)
        if (rows := terminal_rows_for(model, record, strip))  # a strip with no rows has no page
    ]
    return "\n#pagebreak()\n".join(sections)


def _side_headings(model: Model, strip: Id[Item]) -> tuple[str, str]:
    """Ends headings: the strip's shared non-empty markings, else `TERMINAL_LABELS` (pdf-0012)."""
    idx = build_indexes(model)
    terminals = terminal_items(model)
    pairs: set[tuple[str | None, str | None]] = set()
    for child in idx.children_by_item.get(strip, ()):
        if child not in terminals:
            continue
        markings: dict[PortRole, set[str | None]] = {
            PortRole.INTERNAL: set(),
            PortRole.EXTERNAL: set(),
        }
        for function in idx.functions_by_item.get(child, ()):
            for port in idx.ports_by_function.get(function, ()):
                record = ports(model)[port]
                if record.role in markings:
                    markings[record.role].add(record.marking)
        pairs.update(
            product(markings[PortRole.INTERNAL] or {None}, markings[PortRole.EXTERNAL] or {None})
        )
    if len(pairs) == 1:
        internal, external = next(iter(pairs))
        if internal and external:
            return internal, external
    return TERMINAL_LABELS["internal_ends"], TERMINAL_LABELS["external_ends"]


# -- the Bridge column (spec T2, pdf-0007) --------------------------------------------------

_TERMINAL_DATA = TERMINAL_COLUMNS[:-1]  # designation, group, index, internal_ends, external_ends
_TERMINAL_SIDES = ("internal_ends", "external_ends")  # both unbounded text: `1fr` each (pdf-0008)
_BRIDGE_COLUMN_WIDTH_MM = 15  # spec T2 amendment: fixed column width
_BRIDGE_LANE_GAP_MM = 3  # spec T2 amendment: lanes centred in the column, this far apart
_BRIDGE_TICK_HALF_WIDTH_MM = 1
_BRIDGE_STROKE = "0.5pt"


@dataclass(frozen=True, slots=True)
class _BridgeMark:
    """One row's mark in one lane (T2): half-lines `top`/`bottom` (both: through), `tick`."""

    top: bool
    bottom: bool
    tick: bool


def _bridge_spans(groups: tuple[int | None, ...]) -> dict[int, tuple[int, int]]:
    """Each jumper group's (first, last) row index in `groups`, 0-based (spec T2)."""
    first: dict[int, int] = {}
    last: dict[int, int] = {}
    for index, group in enumerate(groups):
        if group is None:
            continue
        first.setdefault(group, index)
        last[group] = index
    return {group: (first[group], last[group]) for group in first}


def _bridge_lanes(spans: dict[int, tuple[int, int]]) -> dict[int, int]:
    """Each group's lane in group-number order; overlapping row spans never share one (T2)."""
    lane_ends: list[int] = []  # lane_ends[lane] is the last row index that lane is used through
    lanes: dict[int, int] = {}
    for group in sorted(spans):
        first, last = spans[group]
        lane = next((i for i, end in enumerate(lane_ends) if end < first), None)
        if lane is None:
            lane = len(lane_ends)
            lane_ends.append(last)
        else:
            lane_ends[lane] = last
        lanes[group] = lane
    return lanes


def _bridge_geometry(groups: tuple[int | None, ...]) -> tuple[tuple[_BridgeMark | None, ...], ...]:
    """One entry per row, a mark (or `None`) per lane (T2); an empty tuple with no group."""
    spans = _bridge_spans(groups)
    lanes = _bridge_lanes(spans)
    lane_count = len(set(lanes.values()))  # distinct lanes used, not `len(lanes)` (one per group)
    rows: list[list[_BridgeMark | None]] = [[None] * lane_count for _ in groups]
    for group, (first, last) in spans.items():
        lane = lanes[group]
        for index in range(first, last + 1):
            rows[index][lane] = _BridgeMark(
                top=index != first, bottom=index != last, tick=groups[index] == group
            )
    return tuple(tuple(row) for row in rows)


def _bridge_lane_x_mm(lane_count: int) -> tuple[float, ...]:
    """Each lane's x offset (mm): centred in the Bridge column, `_BRIDGE_LANE_GAP_MM` apart (T2)."""
    centre = _BRIDGE_COLUMN_WIDTH_MM / 2
    offset = (lane_count - 1) / 2
    return tuple(centre + (index - offset) * _BRIDGE_LANE_GAP_MM for index in range(lane_count))


def _mm(value: float) -> str:
    """`value` as a Typst mm length: `10` not `10.0`, deterministic (source purity)."""
    return f"{value:g}"


def _bridge_mark_typst(mark: _BridgeMark | None, x_mm: float) -> str:
    """One lane's marks for one row as `#place(...)` lines (T2); `y` is % of the cell."""
    if mark is None:
        return ""
    x = _mm(x_mm)
    segments = []
    if mark.top:
        segments.append(
            f"place(top+left, line(start: ({x}mm, 0%), end: ({x}mm, 50%), "
            f"stroke: {_BRIDGE_STROKE}))"
        )
    if mark.bottom:
        segments.append(
            f"place(top+left, line(start: ({x}mm, 50%), end: ({x}mm, 100%), "
            f"stroke: {_BRIDGE_STROKE}))"
        )
    if mark.tick:
        left, right = _mm(x_mm - _BRIDGE_TICK_HALF_WIDTH_MM), _mm(x_mm + _BRIDGE_TICK_HALF_WIDTH_MM)
        segments.append(
            f"place(top+left, line(start: ({left}mm, 50%), end: ({right}mm, 50%), "
            f"stroke: {_BRIDGE_STROKE}))"
        )
    return "".join(f"#{segment}\n" for segment in segments)


def _bridge_cell_typst(
    row_marks: tuple[_BridgeMark | None, ...], lane_xs: tuple[float, ...]
) -> str:
    """One row's Bridge cell (pdf-0007): `breakable: false` scopes `%` to the row; `inset: 0pt`."""
    if not row_marks:
        return 'table.cell(inset: 0pt, text(""))'
    content = "".join(
        _bridge_mark_typst(mark, x) for mark, x in zip(row_marks, lane_xs, strict=True)
    )
    return f"table.cell(inset: 0pt, breakable: false)[{content}]"


def _ends_without_jumpers(
    model: Model, row: TerminalRow
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """`row`'s (internal, external) ends without jumper partners, which the Bridge shows (T2)."""
    all_conductors = conductors(model)

    def kept(ids: tuple[Id[Conductor], ...], ends: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(
            end
            for conductor, end in zip(ids, ends, strict=True)
            if all_conductors[conductor].kind is not ConductorKind.JUMPER
        )

    return kept(row.internal, row.internal_ends), kept(row.external, row.external_ends)


def _terminal_table(
    model: Model,
    rows: tuple[TerminalRow, ...],
    headings: tuple[str, str] = (
        TERMINAL_LABELS["internal_ends"],
        TERMINAL_LABELS["external_ends"],
    ),
) -> str:
    """The TERMINAL_LIST table: data columns, then a drawn Bridge column (pdf-0007, 0008, 0011)."""
    if not rows:
        return ""
    geometry = _bridge_geometry(tuple(row.jumper_group for row in rows))
    lane_xs = _bridge_lane_x_mm(len(geometry[0]) if geometry else 0)
    label = {"internal_ends": headings[0], "external_ends": headings[1]}
    values = []
    for row in rows:
        ends = dict(
            zip(("internal_ends", "external_ends"), _ends_without_jumpers(model, row), strict=True)
        )
        values.append(tuple(ends.get(name, getattr(row, name)) for name in _TERMINAL_DATA))
    kept = _kept_columns(values, len(_TERMINAL_DATA))  # empty columns are not drawn (pdf-0011)
    bridge = any(geometry)  # a strip with no jumper group has an all-empty Bridge column
    if not kept and not bridge:
        return ""
    headers = [label.get(_TERMINAL_DATA[i]) or _humanise(_TERMINAL_DATA[i]) for i in kept] + (
        ["Bridge"] if bridge else []
    )
    header = "table.header(" + ", ".join(f"strong(text({literal(h)}))" for h in headers) + ")"
    cells = [header]
    for row_values, row_marks in zip(values, geometry, strict=True):
        cells.extend(_cell_typst(row_values[i]) for i in kept)
        if bridge:
            cells.append(_bridge_cell_typst(row_marks, lane_xs))
    widths = _widths([_TERMINAL_DATA[i] in _TERMINAL_SIDES for i in kept])
    if bridge:
        widths.append(f"{_BRIDGE_COLUMN_WIDTH_MM}mm")
    return f"#table(columns: ({', '.join(widths)}), stroke: 0.5pt, " + ", ".join(cells) + ")"


def _boards_for(model: Model, record: Document) -> tuple[Id[Item], ...]:
    """The CONNECTOR_LIST boards: the item, else a unit's own (U6), else the location's."""
    if record.item is not None:
        return (record.item,) if record.item in boards(model) else ()
    if (unit := document_unit(model, record)) is not None:
        return unit_boards(model, unit)
    location = record.location
    if location is None:
        return ()
    at_location = set(items_at(model, location))
    return tuple(board for board in boards(model) if board in at_location)


def connector_list_page(model: Model, record: Document) -> str:
    """The CONNECTOR_LIST section: a headed table per board (P9); unit-relative (pdf-0012)."""
    unit = document_unit(model, record)
    sections = [
        _list_heading(model, board, unit)
        + _table((*CONNECTOR_COLUMNS, *PIN_COLUMNS), lines, ("net",))
        for board in _boards_for(model, record)
        if (lines := pin_lines(connector_rows_for(model, record, board)))  # no rows, no page
    ]
    return "\n#pagebreak()\n".join(sections)
