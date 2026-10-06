"""Derive rows formatted as CSV (spec sections 6 and 10)."""

import csv
import io
from typing import TYPE_CHECKING

from fransys_model.derive import (
    BOM_COLUMNS,
    CABLE_LIST_COLUMNS,
    CONNECTOR_COLUMNS,
    DESIGNATION_COLUMNS,
    PIN_COLUMNS,
    PLC_COLUMNS,
    TERMINAL_COLUMNS,
    TERMINAL_LABELS,
    WIRE_COLUMNS,
    WIRE_LABELS,
    bom_lines,
    cable_list_rows,
    cell_text,
    column_rows,
    connector_rows,
    designation_list,
    pin_lines,
    plc_channel_rows,
    terminal_rows,
    wire_rows,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from fransys_model.derive import TopLevelScope
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import AspectNode, Item, Unit

# The two terminal ends columns are the terminal's port roles, internal then external (owner
# ruling 2026-09-24): their CSV headers are the derive labels ("Side A", "Side B") in this
# file's snake_case (`side_a`, `side_b`), not the row's field names.
_TERMINAL_LABELS = {
    field: label.replace(" ", "_").lower() for field, label in TERMINAL_LABELS.items()
}


def _write(columns: tuple[str, ...], lines: Iterable[Iterable[object]]) -> str:
    """The header of `columns`, then one line per item of `lines` in the order given."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=",", quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
    writer.writerow(columns)
    writer.writerows([cell_text(value) for value in line] for line in lines)
    return buffer.getvalue()


def _csv(
    rows: Iterable[object], columns: tuple[str, ...], labels: dict[str, str] | None = None
) -> str:
    """One line per row, each the row's fields named by `columns`.

    The header cell of a column is its name, or `labels[name]` where `labels` has one.
    """
    header = tuple((labels or {}).get(name, name) for name in columns)
    return _write(header, column_rows(rows, columns))


def terminal_csv(
    model: Model,
    strip: Id[Item],
    *,
    unit: Id[Unit] | None = None,
    context: Id[AspectNode] | None = None,
) -> str:
    """Write the terminal connection list of one strip as CSV.

    Formats ``fransys_model.derive.queries.terminal_rows``, one row per terminal
    child of `strip`, including unused terminals. Side A is the internal ports' far ends,
    side B the external ports'; ``jumper_group`` names the bridge. `unit` and `context` pass
    through to `terminal_rows` (`derive.list_context` for `context`). Pure.

    Args:
        model: A frozen, numbered model.
        strip: The terminal-strip item.
        unit: Keep only that unit's rows; `None` is the whole model.
        context: The location node the list is printed for; `None` prints full paths.

    Returns:
        The CSV text. Same model digest, same bytes.
    """
    return _csv(
        terminal_rows(model, strip, unit=unit, context=context), TERMINAL_COLUMNS, _TERMINAL_LABELS
    )


def plc_csv(
    model: Model, *, unit: Id[Unit] | None = None, context: Id[AspectNode] | None = None
) -> str:
    """Write the PLC channel report as CSV.

    Formats ``fransys_model.derive.queries.plc_channel_rows``: channel, signal, where the
    channel is wired to (`wired_to`) and signal name, one row per allocated PLC channel.
    `unit` and `context` pass through (units spec U6). Pure.

    Args:
        model: A frozen, numbered model with PLC allocation applied.
        unit: Keep only that unit's channels; `None` is the whole model.
        context: The location node the list is printed for, as `terminal_csv`'s.

    Returns:
        The CSV text. Same model digest, same bytes.
    """
    return _csv(plc_channel_rows(model, unit=unit, context=context), PLC_COLUMNS)


def bom_csv(
    model: Model, scope: Id[Item] | Id[AspectNode] | Id[Unit] | TopLevelScope | None = None
) -> str:
    """Write the bill of materials as CSV.

    Formats ``fransys_model.derive.queries.bom_lines``, one row per part used by an
    `installed=True` item. `scope` restricts the lines as `bom_lines` does (units spec U5,
    reports-0002). Pure.

    Args:
        model: A frozen, numbered model.
        scope: An item, location node, unit or `derive.TOP_LEVEL`; `None` is the whole model.

    Returns:
        The CSV text. Same model digest, same bytes.

    Raises:
        SchemaError: `scope` is neither an item, an aspect node nor a unit of `model`.
    """
    return _csv(bom_lines(model, scope), BOM_COLUMNS)


def wires_csv(
    model: Model, *, unit: Id[Unit] | None = None, context: Id[AspectNode] | None = None
) -> str:
    """Write the wire list as CSV (V8).

    Formats ``fransys_model.derive.wire_rows``, one row per wire: `from`, `to`, `colour`,
    `cross_section_mm2` and the `label` printed at both ends. `unit` and `context` pass
    through (units spec U6). Pure.

    Args:
        model: A frozen, numbered model.
        unit: Keep only that unit's conductors; `None` is the whole model.
        context: The location node the list is printed for, as `terminal_csv`'s.

    Returns:
        The CSV text. Same model digest, same bytes.
    """
    return _csv(wire_rows(model, unit=unit, context=context), WIRE_COLUMNS, WIRE_LABELS)


def designations_csv(model: Model, *, unit: Id[Unit] | None = None) -> str:
    """Write the designation (tag) list as CSV.

    Formats ``fransys_model.derive.queries.designation_list``, one row per item,
    sorted by designation. `unit` passes through (units spec U6). Pure.

    Args:
        model: A frozen, numbered model.
        unit: Keep only that unit's items; `None` is the whole model.

    Returns:
        The CSV text. Same model digest, same bytes.
    """
    return _csv(designation_list(model, unit=unit), DESIGNATION_COLUMNS)


def connectors_csv(
    model: Model,
    board: Id[Item],
    *,
    unit: Id[Unit] | None = None,
    context: Id[AspectNode] | None = None,
) -> str:
    """Write the connector pinout list of one board as CSV.

    Formats ``fransys_model.derive.queries.connector_rows``: each board-edge connector, its
    pins, the net on each pin, and what it mates with. One line per pin, the connector's fields
    repeated on each line, so an engineer can filter the file; a connector with no pins has no
    line. Pure.

    Args:
        model: A frozen, numbered model.
        board: The board item; its part carries a ``pcb`` facet.
        unit: Keep only that unit's rows; `None` is the whole model.
        context: The location node the list is printed for, as `terminal_csv`'s.

    Returns:
        The CSV text. Same model digest, same bytes.
    """
    return _write(
        (*CONNECTOR_COLUMNS, *PIN_COLUMNS),
        pin_lines(connector_rows(model, board, unit=unit, context=context)),
    )


def cables_csv(model: Model) -> str:
    """Write the top-level cable list as CSV (units spec U3, root decision 0016).

    Formats ``fransys_model.derive.queries.cable_list_rows``, one row per `unit=None` cable.
    It takes no `unit=`: those cables are top-level by construction, so a unit scope is empty.

    Args:
        model: A frozen, numbered model.

    Returns:
        The CSV text. Same model digest, same bytes.
    """
    return _csv(cable_list_rows(model), CABLE_LIST_COLUMNS)
