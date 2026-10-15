"""Laid-out model to SVG pages (6 and 9)."""

from typing import TYPE_CHECKING

from fransys_model.kernel import render_id
from fransys_model.layout import DrawingSet, Page, layout_of, sheet_format_of

from ._fan_outs import fan_outs_group
from ._harness import connector_boxes_group, harness_lines_group
from ._junctions import junctions_group
from ._labels import labels_group
from ._markers import markers_group
from ._outlines import outlines_group
from ._ref_fill import checked_tints
from ._routes import routes_group
from ._style import style_block
from ._symbols import symbols_group

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fransys_model.kernel import Model


def _ordered_pages(model: Model) -> tuple[Page, ...]:
    """Every `layout.page` of `model`, ordered `(drawing_set.number, page.number)`."""
    drawing_sets = layout_of(model, DrawingSet)
    pages_by_id = layout_of(model, Page)
    return tuple(
        sorted(
            pages_by_id.values(),
            key=lambda page: (drawing_sets[page.drawing_set].number, page.number),
        )
    )


def _render_page(model: Model, page: Page, tints: Sequence[str]) -> str:
    """One page's SVG: viewBox, style, then the groups in drawing order.

    Order: outlines, symbols, routes, harness lines, fan-outs,
    connector boxes, junctions, markers, labels.
    """
    sheet = sheet_format_of(model, page.sheet_format)
    width_mm, height_mm = sheet.width_mm, sheet.height_mm
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width_mm}mm" height="{height_mm}mm" '
        f'viewBox="0 0 {width_mm} {height_mm}">'
        f"{style_block()}"
        f"{outlines_group(model, page)}"
        f"{symbols_group(model, page)}"
        f"{routes_group(model, page)}"
        f"{harness_lines_group(model, page)}"
        f"{fan_outs_group(model, page)}"
        f"{connector_boxes_group(model, page)}"
        f"{junctions_group(model, page)}"
        f"{markers_group(model, page, tints)}"
        f"{labels_group(model, page)}"
        "</svg>"
    )


def pages(model: Model, *, tints: Sequence[str]) -> frozendict[str, str]:
    """Render every schematic page of a laid-out model to SVG.

    One page per `layout.page`, keyed by `render_id(page.id)`, ordered by
    `(drawing_set.number, page.number)`. Each page is a sheet-sized SVG with the groups
    listed in the package README, and no frame, grid or title block. Pure.

    Args:
        model: A laid-out model (its ``layout.*`` records are present).
        tints: Eight fill colours (``#rrggbb``), one per net-reference slot, or none for
            no fills. Any other count raises ``ValueError``.

    Returns:
        Page key to SVG text.
    """
    tints = checked_tints(tints)
    return frozendict(
        {render_id(page.id): _render_page(model, page, tints) for page in _ordered_pages(model)}
    )
