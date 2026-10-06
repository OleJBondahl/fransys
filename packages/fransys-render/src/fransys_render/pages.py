"""Laid-out model to SVG pages (spec sections 4, 6 and 9)."""

from typing import TYPE_CHECKING

from fransys_model.kernel import render_id
from fransys_model.layout import DrawingSet, Page, layout_of, sheet_format_of

from ._junctions import junctions_group
from ._labels import labels_group
from ._markers import markers_group
from ._outlines import outlines_group
from ._routes import routes_group
from ._style import style_block
from ._symbols import symbols_group

if TYPE_CHECKING:
    from fransys_model.kernel import Model


def _ordered_pages(model: Model) -> tuple[Page, ...]:
    """Every `layout.page` of `model`, ordered `(drawing_set.number, page.number)` (D4)."""
    drawing_sets = layout_of(model, DrawingSet)
    pages_by_id = layout_of(model, Page)
    return tuple(
        sorted(
            pages_by_id.values(),
            key=lambda page: (drawing_sets[page.drawing_set].number, page.number),
        )
    )


def _render_page(model: Model, page: Page) -> str:
    """One page's SVG: viewBox, style, outlines, symbols, routes, junctions, markers, labels."""
    sheet = sheet_format_of(model, page.sheet_format)
    width_mm, height_mm = sheet.width_mm, sheet.height_mm
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width_mm}mm" height="{height_mm}mm" '
        f'viewBox="0 0 {width_mm} {height_mm}">'
        f"{style_block(sheet.module_mm)}"
        f"{outlines_group(model, page)}"
        f"{symbols_group(model, page)}"
        f"{routes_group(model, page)}"
        f"{junctions_group(model, page)}"
        f"{markers_group(model, page)}"
        f"{labels_group(model, page)}"
        "</svg>"
    )


def pages(model: Model) -> frozendict[str, str]:
    """Render every schematic page of a laid-out model to SVG.

    One page per `layout.page`, keyed by `render_id(page.id)` (D4), ordered by
    `(drawing_set.number, page.number)`. Each page is a sheet-sized SVG (D5) with the groups
    listed in the package README, and no frame, grid or title block (D9). Pure.

    Args:
        model: A laid-out model (its ``layout.*`` records are present).

    Returns:
        Page key to SVG text.
    """
    return frozendict(
        {render_id(page.id): _render_page(model, page) for page in _ordered_pages(model)}
    )
