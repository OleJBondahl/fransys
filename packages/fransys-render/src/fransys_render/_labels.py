"""Label text: one `<text>` per `layout.label` on a page, top-down, left to right (`by_place`)."""

from collections import Counter
from typing import TYPE_CHECKING
from xml.sax.saxutils import escape

from fransys_model.derive import item_installed, text_room_g
from fransys_model.derive.contact_rows import (
    column_split,
    column_x,
    contact_rows,
    table_geometry,
)
from fransys_model.derive.drawing_text import (
    CONTACT_SLOTS,
    contact_heading,
    label_text,
)
from fransys_model.derive.grid_mm import grid_to_mm
from fransys_model.derive.order import drawn_on_page
from fransys_model.derive.print_sizes import ASCENT_RATIO
from fransys_model.layout import Label, profile_of_page, sheet_format_of
from fransys_model.vocab import functions, ports

from ._numbers import format_decimal, printed_font_mm

if TYPE_CHECKING:
    from fransys_model.kernel import Model
    from fransys_model.layout import Page, Profile, SheetFormat


def labels_on_page(model: Model, page: Page) -> tuple[Label, ...]:
    """Every `layout.label` on `page`, top-down, left to right (`by_place`)."""
    return drawn_on_page(model, Label, page)


def _label_class(model: Model, label: Label) -> str:
    """`label not-installed` when the label's subject's item has `installed=False`."""
    if label.function is not None:
        item = functions(model)[label.function].item
    elif label.port is not None:
        item = functions(model)[ports(model)[label.port].function].item
    else:
        return "label"
    return "label" if item_installed(model, item) else "label not-installed"


def _contact_image(model: Model, sheet: SheetFormat, profile: Profile, label: Label) -> str:
    """A coil's contact image, at the label's measured box."""
    step = text_room_g(profile.text_height_mm, sheet.module_mm)
    pad = profile.marker_padding
    font_mm = printed_font_mm(profile.text_height_mm)
    css_class = _label_class(model, label)

    def mm_x(x: int):  # noqa: ANN202 -- one-line closure returning `format_decimal`'s own `-> str`, restating it adds nothing
        return format_decimal(grid_to_mm(sheet.content_x_mm, x, sheet.module_mm))

    def mm_y(y: int):  # noqa: ANN202 -- same closure shape as `mm_x` just above, for the y axis
        return format_decimal(grid_to_mm(sheet.content_y_mm, y, sheet.module_mm))

    def text(x: int, top: int, value: str) -> str:
        baseline = grid_to_mm(sheet.content_y_mm, top, sheet.module_mm) + font_mm * ASCENT_RATIO
        return (
            f'<text class="{css_class}" x="{mm_x(x)}" y="{format_decimal(baseline)}" '
            f'font-size="{format_decimal(font_mm)}">{escape(value)}</text>'
        )

    heading = contact_heading(model, label)  # layout-0170: a table sharing its foot names its coil
    rows = contact_rows(model, label)
    tallest = max(Counter(row.column for row in rows).values(), default=0)
    geo = table_geometry(tallest, step, pad, headed=bool(heading))
    x0, y0, split_x = label.x, label.y, label.x + column_split(label.width)
    no_x, nc_x = column_x(label.width, pad)
    parts = [
        *([text(x0 + no_x, y0 + geo.heading, heading)] if heading else []),
        text(x0 + no_x, y0 + geo.titles, "NO"),
        text(x0 + nc_x, y0 + geo.titles, "NC"),
        (
            f'<line class="marker" x1="{mm_x(x0)}" y1="{mm_y(y0 + geo.rule)}" '
            f'x2="{mm_x(x0 + label.width)}" y2="{mm_y(y0 + geo.rule)}"/>'
        ),
        (
            f'<line class="marker" x1="{mm_x(split_x)}" y1="{mm_y(y0 + geo.columns)}" '
            f'x2="{mm_x(split_x)}" y2="{mm_y(y0 + label.height)}"/>'
        ),
    ]
    parts.extend(text(row.x, row.y, row.text) for row in rows)
    return "".join(parts)


def _label_element(model: Model, sheet: SheetFormat, profile: Profile, label: Label) -> str:
    """One label as a `<text>` element: position, class and escaped text."""
    if label.slot in CONTACT_SLOTS:
        return _contact_image(model, sheet, profile, label)
    top_mm = grid_to_mm(sheet.content_y_mm, label.y, sheet.module_mm)
    font_mm = printed_font_mm(profile.text_height_mm)
    baseline_mm = top_mm + font_mm * ASCENT_RATIO
    x_mm = grid_to_mm(sheet.content_x_mm, label.x, sheet.module_mm)
    css_class = _label_class(model, label)
    return (
        f'<text class="{css_class}" x="{format_decimal(x_mm)}" y="{format_decimal(baseline_mm)}" '
        f'font-size="{format_decimal(font_mm)}">'
        f"{escape(label_text(model, label))}</text>"
    )


def labels_group(model: Model, page: Page) -> str:
    """Every label on `page` as one `<text>` each, in id order, `not-installed` if uninstalled."""
    sheet = sheet_format_of(model, page.sheet_format)
    profile = profile_of_page(model, page)
    return "".join(
        _label_element(model, sheet, profile, label) for label in labels_on_page(model, page)
    )
