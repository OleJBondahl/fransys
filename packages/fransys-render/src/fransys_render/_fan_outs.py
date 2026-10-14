"""Harness fan-out legs: one plain wire `<polyline>` each, no label, dot or mark (render-0010)."""

from typing import TYPE_CHECKING

from fransys_model.derive.order import drawn_on_page
from fransys_model.layout import HarnessFanOut, sheet_format_of

from ._numbers import point_mm

if TYPE_CHECKING:
    from fransys_model.kernel import Model
    from fransys_model.layout import Page


def fan_outs_group(model: Model, page: Page) -> str:
    """Every fan-out leg on `page` as one wire `<polyline>`, fan-outs by place, legs by `index`."""
    sheet = sheet_format_of(model, page.sheet_format)
    return "".join(
        '<polyline class="wire" points="'
        + " ".join(point_mm(sheet, point.x, point.y) for point in leg.points)
        + '"/>'
        for fan_out in drawn_on_page(model, HarnessFanOut, page)
        for leg in fan_out.legs
    )
