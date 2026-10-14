"""A contact table's geometry: the one place its lines and rows are worked out (model-0216, CR2).

Layout sizes the table by `table_geometry(...).height`; render and `contact_rows` place the
heading, the rule and each row from the same values. The row step is the profile's text room.
"""

from fransys_model.layout import Label, Page, layout_of, profile_of_page, sheet_format_of
lazy from fransys_model.kernel import Model

from .drawing_text import contact_heading, image_entries
from .rows_nav import ContactRow, TableGeometry
from .text_size import text_room_g
from .text_width import text_width

__all__ = ["column_split", "column_x", "contact_rows", "heading_room", "table_geometry"]


def heading_room(step: int, *, headed: bool) -> int:
    """The room a table's heading line takes above its columns: one row step, or none."""
    return step if headed else 0


def column_split(width: int) -> int:
    """The x of the divider between the NO and the NC column, from the table's left edge."""
    return width // 2


def table_geometry(rows: int, step: int, pad: int, *, headed: bool) -> TableGeometry:
    """The lines of a table of `rows` rows, each `step` high, with `pad` around the texts.

    Heading line (when `headed`), then the "NO"/"NC" line, the rule, the rows and a last pad.
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


def contact_rows(model: Model, label: Label) -> tuple[ContactRow, ...]:
    """The rows of `label`'s contact table in print order: the NO column, then the NC column.

    Each row's box is its text's measured width (`text_width`), one row step high, at the row's
    top from `table_geometry`. The step is the page's profile text room, as render draws it.
    """
    page = layout_of(model, Page)[label.page]
    profile = profile_of_page(model, page)
    step = text_room_g(profile.text_height_mm, sheet_format_of(model, page.sheet_format).module_mm)
    no, nc = image_entries(model, label)
    top = (
        label.y
        + table_geometry(
            0, step, profile.marker_padding, headed=bool(contact_heading(model, label))
        ).first_row
    )
    xs = column_x(label.width, profile.marker_padding)
    return tuple(
        ContactRow(
            column=column,
            text=text,
            partner=partner,
            x=label.x + x,
            y=top + index * step,
            width=text_width(text, height=step),
            height=step,
        )
        for column, entries, x in (("NO", no, xs[0]), ("NC", nc, xs[1]))
        for index, (text, partner) in enumerate(entries)
    )
