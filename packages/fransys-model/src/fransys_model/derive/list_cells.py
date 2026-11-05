"""The one text of a list cell and the field extraction every list output reads (derive-queries.md).

Which fields of each row shape a list prints stay in `derive.columns`.
"""

from enum import Enum
lazy from collections.abc import Iterable

lazy from fransys_model.elecdef import Gender
lazy from fransys_model.kernel import Model

lazy from .columns import list_columns, list_pdf_columns
lazy from .rows import ConnectorRow

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
        case Gender():
            return cell.name.lower()
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


def pin_lines(model: Model, rows: Iterable[ConnectorRow]) -> list[tuple[object, ...]]:
    """One line per pin of each connector row, in the `connectors` column order.

    A column that is one of the connector list's `pdf_columns` is read from the pin, the rest
    from the connector row.
    """
    columns = list_columns(model, "connectors")
    pin_fields = list_pdf_columns(model, "connectors")
    return [tuple(column_values(pin if name in pin_fields else row, (name,))[0] for name in columns) for row in rows for pin in row.pins]
