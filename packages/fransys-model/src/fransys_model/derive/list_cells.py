"""The one text of a list cell and the field extraction every list output reads (derive-queries.md).

Which fields of each row shape a list prints (`*_COLUMNS`) stay in `derive.rows`.
"""

from enum import Enum
lazy from collections.abc import Iterable

from .rows import CONNECTOR_COLUMNS, PIN_COLUMNS, ConnectorRow

CELL_SEPARATOR = "; "


def cell_parts(cell: tuple[object, ...]) -> tuple[str, ...]:
    """The non-empty text of each part of a tuple-valued list cell; a nested tuple is one part.

    Args:
        cell: A list cell's raw tuple value.

    Returns:
        `cell_text` of each part, empty ones left out.
    """
    return tuple(text for part in cell if (text := cell_text(part)))


def cell_text(cell: object) -> str:
    """`cell` as the text of one list cell: `None` empty, an enum its value, a tuple its parts.

    A tuple's parts are joined by `CELL_SEPARATOR`, empty parts left out (`cell_parts`).

    Args:
        cell: A row field's raw value.

    Returns:
        The text one list cell prints for it.
    """
    match cell:
        case None:
            return ""
        case Enum():
            return str(cell.value)
        case tuple():
            return CELL_SEPARATOR.join(cell_parts(cell))
        case _:
            return str(cell)


def column_values(record: object, columns: tuple[str, ...]) -> tuple[object, ...]:
    """`record`'s fields named by `columns`, in that order.

    Args:
        record: A row (or a `ConnectorPin`) to read fields of.
        columns: The field names to read, in print order.

    Returns:
        `record`'s value for each name in `columns`, in that order.
    """
    return tuple(getattr(record, name) for name in columns)


def column_rows(records: Iterable[object], columns: tuple[str, ...]) -> list[tuple[object, ...]]:
    """One `column_values` line per record, in the order given.

    Args:
        records: The rows to read, in the order to print them.
        columns: The field names to read, in print order.

    Returns:
        One `column_values` tuple per record, in `records`' order.
    """
    return [column_values(record, columns) for record in records]


def pin_lines(rows: Iterable[ConnectorRow]) -> list[tuple[object, ...]]:
    """One line per pin of each connector row: the connector's fields, then the pin's.

    Args:
        rows: The connector rows to print, in the order to print them.

    Returns:
        One tuple per pin: `CONNECTOR_COLUMNS` of its row, then `PIN_COLUMNS` of the pin.
    """
    lines: list[tuple[object, ...]] = []
    for row in rows:
        head = column_values(row, CONNECTOR_COLUMNS)
        lines.extend((*head, *column_values(pin, PIN_COLUMNS)) for pin in row.pins)
    return lines
