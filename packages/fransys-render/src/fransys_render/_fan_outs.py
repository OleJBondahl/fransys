"""Harness fan-out legs: one plain wire `<polyline>` each, no label, dot or mark (render-0010)."""

from typing import TYPE_CHECKING

from fransys_model.layout import HarnessFanOut, page_slice, sheet_format_of

from ._routes import _point_mm

if TYPE_CHECKING:
    from fransys_model.kernel import Model
    from fransys_model.layout import Page


def fan_outs_group(model: Model, page: Page) -> str:
    """Every fan-out leg on `page` as one wire `<polyline>`, fan-outs by `id`, legs by `index`."""
    sheet = sheet_format_of(model, page.sheet_format)
    return "".join(
        '<polyline class="wire" points="'
        + " ".join(_point_mm(sheet, point.x, point.y) for point in leg.points)
        + '"/>'
        for fan_out in page_slice(model, HarnessFanOut, page)
        for leg in fan_out.legs
    )
