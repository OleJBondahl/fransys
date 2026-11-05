"""Derive rows formatted as CSV."""

import csv
import io
from typing import TYPE_CHECKING

from fransys_model.derive import (
    bom_lines,
    cable_list_rows,
    cell_text,
    column_rows,
    connector_rows,
    core_list_rows,
    csv_dialect,
    designation_list,
    export_form_of,
    list_columns,
    list_csv_header,
    pin_lines,
    plc_channel_rows,
    terminal_rows,
    wire_rows,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from fransys_model.derive import AspectNodeId, ItemId, TopLevelScope, UnitId
    from fransys_model.kernel import Model


def _write(model: Model, header: tuple[str, ...], lines: Iterable[Iterable[object]]) -> str:
    """The `header`, then one line per item of `lines` in the order given, in the CSV form."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, csv_dialect(export_form_of(model)))
    writer.writerow(header)
    writer.writerows([cell_text(value) for value in line] for line in lines)
    return buffer.getvalue()


def _header(model: Model, name: str) -> tuple[str, ...]:
    """The CSV header cells of list `name`: the text of each column's `csv` word."""
    return tuple(list_csv_header(model, name, field) for field in list_columns(model, name))


def _csv(model: Model, rows: Iterable[object], columns: tuple[str, ...]) -> str:
    """One line per row, each the row's fields named by `columns`; the header is their names."""
    return _write(model, columns, column_rows(rows, columns))


def _list_csv(model: Model, name: str, rows: Iterable[object]) -> str:
    """One line per row of list `name`, under the `csv` headers of its columns."""
    lines = column_rows(rows, list_columns(model, name))
    return _write(model, _header(model, name), lines)


def terminal_csv(
    model: Model,
    strip: ItemId,
    *,
    unit: UnitId | None = None,
    context: AspectNodeId | None = None,
) -> str:
    """Write the terminal connection list of one strip as CSV.

    Formats ``fransys_model.derive.queries.terminal_rows``, one row per terminal child of `strip`,
    including unused terminals. Side A is the internal ports' far ends, side B the external ports';
    ``jumper_group`` names the bridge. `unit` and `context` pass through (`derive.list_context`).

    Args:
        model: A frozen, numbered model.
        strip: The terminal-strip item.
        unit: Keep only that unit's rows; `None` is the whole model.
        context: The location node the list is printed for; `None` prints full paths.

    Returns:
        The CSV text. Same model digest, same bytes.
    """
    return _list_csv(model, "terminal", terminal_rows(model, strip, unit=unit, context=context))


def plc_csv(model: Model, *, unit: UnitId | None = None, context: AspectNodeId | None = None) -> str:
    """Write the PLC channel report as CSV.

    Formats ``fransys_model.derive.queries.plc_channel_rows``: channel, signal, where the
    channel is wired to (`wired_to`) and signal name, one row per allocated PLC channel.
    `unit` and `context` pass through. Pure.

    Args:
        model: A frozen, numbered model with PLC allocation applied.
        unit: Keep only that unit's channels; `None` is the whole model.
        context: The location node the list is printed for, as `terminal_csv`'s.

    Returns:
        The CSV text. Same model digest, same bytes.
    """
    return _list_csv(model, "plc", plc_channel_rows(model, unit=unit, context=context))


def bom_csv(model: Model, scope: ItemId | AspectNodeId | UnitId | TopLevelScope | None = None) -> str:
    """Write the bill of materials as CSV.

    Formats ``fransys_model.derive.queries.bom_lines``, one row per part used by an
    `installed=True` item. `scope` restricts the lines as `bom_lines` does (reports-0002). Pure.

    Args:
        model: A frozen, numbered model.
        scope: An item, location node, unit or `derive.TOP_LEVEL`; `None` is the whole model.

    Returns:
        The CSV text. Same model digest, same bytes.

    Raises:
        SchemaError: `scope` is neither an item, an aspect node nor a unit of `model`.
    """
    return _list_csv(model, "bom", bom_lines(model, scope))


def wires_csv(model: Model, *, unit: UnitId | None = None, context: AspectNodeId | None = None) -> str:
    """Write the wire list as CSV.

    Formats ``fransys_model.derive.wire_rows``, one row per wire: `from`, `to`, `colour`,
    `cross_section_mm2` and the `ends` printed at both ends. `unit` and `context` pass
    through. Pure.

    Args:
        model: A frozen, numbered model.
        unit: Keep only that unit's conductors; `None` is the whole model.
        context: The location node the list is printed for, as `terminal_csv`'s.

    Returns:
        The CSV text. Same model digest, same bytes.
    """
    return _list_csv(model, "wires", wire_rows(model, unit=unit, context=context))


def designations_csv(model: Model, *, unit: UnitId | None = None) -> str:
    """Write the designation (tag) list as CSV.

    Formats ``fransys_model.derive.queries.designation_list``, one row per item,
    sorted by designation. `unit` passes through. Pure.

    Args:
        model: A frozen, numbered model.
        unit: Keep only that unit's items; `None` is the whole model.

    Returns:
        The CSV text. Same model digest, same bytes.
    """
    return _list_csv(model, "designations", designation_list(model, unit=unit))


def connectors_csv(
    model: Model,
    board: ItemId,
    *,
    unit: UnitId | None = None,
    context: AspectNodeId | None = None,
) -> str:
    """Write the connector pinout list of one board as CSV.

    Formats ``fransys_model.derive.queries.connector_rows``: each board-edge connector, its pins,
    the net on each pin, and what it mates with. One line per pin, the connector's fields repeated
    on each line, so an engineer can filter the file; a connector with no pins has no line.

    Args:
        model: A frozen, numbered model.
        board: The board item; its part carries a ``pcb`` facet.
        unit: Keep only that unit's rows; `None` is the whole model.
        context: The location node the list is printed for, as `terminal_csv`'s.

    Returns:
        The CSV text. Same model digest, same bytes.
    """
    return _write(
        model,
        _header(model, "connectors"),
        pin_lines(model, connector_rows(model, board, unit=unit, context=context)),
    )


def cables_csv(model: Model, *, unit: UnitId | None = None) -> str:
    """Write the cable list as CSV (root decision 0016).

    Formats ``fransys_model.derive.queries.cable_list_rows``, one row per cable of `unit`
    (top-level cables for `unit=None`). Pure.

    Args:
        model: A frozen, numbered model.
        unit: The unit whose cables to list, or None for the system.

    Returns:
        The CSV text. Same model digest, same bytes.
    """
    return _list_csv(model, "cables", cable_list_rows(model, unit=unit))


def cores_csv(model: Model, *, unit: UnitId | None = None) -> str:
    """Write the core list as CSV (reports-0005).

    Formats ``fransys_model.derive.core_list_rows``, one row per core of every cable
    ``cables_csv`` lists for `unit`: its ends, its pair word and its spare mark. Pure.

    Args:
        model: A frozen, numbered model.
        unit: The unit whose cables to list, or None for the system.

    Returns:
        The CSV text. Same model digest, same bytes.
    """
    return _list_csv(model, "cores", core_list_rows(model, unit=unit))
