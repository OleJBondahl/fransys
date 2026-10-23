"""A contact table's geometry: the one place its lines and rows are worked out (model-0216, CR2).

Layout sizes the table by `table_geometry(...).height`; render and `contact_rows` place the
heading, the rule and each row from the same values. The row step is the profile's text room.
"""

from .rows_nav import TableGeometry

__all__ = [
    "column_split",
    "column_x",
    "heading_room",
    "table_geometry",
]


def heading_room(step: int, *, headed: bool) -> int:
    """The room a table's heading line takes above its columns: one row step, or none."""
    return step if headed else 0


def column_split(width: int) -> int:
    """The x of the divider between the NO and the NC column, from the table's left edge."""
    return width // 2


def table_geometry(rows: int, step: int, pad: int, *, headed: bool) -> TableGeometry:
    """The lines of a table of `rows` rows, each `step` high, with `pad` around the texts.

    Heading line (when `headed`), then the column titles line, the rule, the rows and a last pad.
    """
    columns = heading_room(step, headed=headed)
    rule = columns + pad + step
    first_row = rule + pad
    return TableGeometry(
        heading=0,
        columns=columns,
        titles=columns + pad,
        rule=rule,
        first_row=first_row,
        height=first_row + rows * step + pad,
    )


def column_x(width: int, pad: int) -> tuple[int, int]:
    """The x of the NO and the NC column's texts from the table's left edge."""
    return pad, column_split(width) + pad
