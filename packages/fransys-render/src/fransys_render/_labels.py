"""Label text (D7): one `<text>` per `layout.label` on a page, ordered by `id` (D11)."""

from typing import TYPE_CHECKING
from xml.sax.saxutils import escape

from fransys_model.derive.drawing_text import contact_image, label_text
from fransys_model.layout import Label, page_slice, profile_of, sheet_format_of
from fransys_model.vocab import functions, items, ports

from ._constants import ASCENT_RATIO
from ._numbers import format_decimal, grid_to_mm

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.layout import Page, Profile, SheetFormat
    from fransys_model.vocab import Item


def labels_on_page(model: Model, page: Page) -> tuple[Label, ...]:
    """Every `layout.label` on `page`, ordered by `id` (D11)."""
    return page_slice(model, Label, page)


def _item_installed(model: Model, item: Id[Item]) -> bool:
    return items(model)[item].installed


def _not_installed(model: Model, label: Label) -> bool:
    """D10: a label whose subject's item has `installed=False`."""
    if label.function is not None:
        return not _item_installed(model, functions(model)[label.function].item)
    if label.port is not None:
        function = functions(model)[ports(model)[label.port].function]
        return not _item_installed(model, function.item)
    return False


def _contact_image(model: Model, sheet: SheetFormat, profile: Profile, label: Label) -> str:
    """C19: a coil's contact image, at the label's measured box."""
    no, nc = contact_image(model, label)
    width, height = label.width, label.height
    step = profile.text_height
    pad = profile.marker_padding
    half = width // 2
    font_mm = grid_to_mm(0, step, sheet.module_mm)
    css_class = "label not-installed" if _not_installed(model, label) else "label"

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

    x0, y0 = label.x, label.y
    rule = y0 + pad + step
    parts = [
        text(x0 + pad, y0 + pad, "NO"),
        text(x0 + half + pad, y0 + pad, "NC"),
        (
            f'<line class="marker" x1="{mm_x(x0)}" y1="{mm_y(rule)}" x2="{mm_x(x0 + width)}" '
            f'y2="{mm_y(rule)}"/>'
        ),
        (
            f'<line class="marker" x1="{mm_x(x0 + half)}" y1="{mm_y(y0)}" '
            f'x2="{mm_x(x0 + half)}" y2="{mm_y(y0 + height)}"/>'
        ),
    ]
    for row, entry in enumerate(no):
        parts.append(text(x0 + pad, rule + pad + row * step, entry))
    for row, entry in enumerate(nc):
        parts.append(text(x0 + half + pad, rule + pad + row * step, entry))
    return "".join(parts)


def _label_element(model: Model, sheet: SheetFormat, profile: Profile, label: Label) -> str:
    """One label as a `<text>` element: position, class and escaped text (D7, D10)."""
    if label.slot == "contacts":
        return _contact_image(model, sheet, profile, label)
    top_mm = grid_to_mm(sheet.content_y_mm, label.y, sheet.module_mm)
    font_size_mm = grid_to_mm(0, profile.text_height, sheet.module_mm)
    baseline_mm = top_mm + font_size_mm * ASCENT_RATIO
    x_mm = grid_to_mm(sheet.content_x_mm, label.x, sheet.module_mm)
    css_class = "label not-installed" if _not_installed(model, label) else "label"
    return (
        f'<text class="{css_class}" x="{format_decimal(x_mm)}" y="{format_decimal(baseline_mm)}" '
        f'font-size="{format_decimal(font_size_mm)}">'
        f"{escape(label_text(model, label))}</text>"
    )


def labels_group(model: Model, page: Page) -> str:
    """Every label on `page` as one `<text>` each, D11 order, `not-installed` class per D10."""
    sheet = sheet_format_of(model, page.sheet_format)
    profile = profile_of(model)
    return "".join(
        _label_element(model, sheet, profile, label) for label in labels_on_page(model, page)
    )
