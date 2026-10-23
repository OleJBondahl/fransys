"""The invisible links over a drawing: each cross reference opens the partner's sheet (NV1, NV2)."""

from typing import TYPE_CHECKING

from fransys_model.derive import mm_per_division
from fransys_model.derive.grid_mm import grid_to_mm

if TYPE_CHECKING:
    from fransys_model.derive import SheetRow
    from fransys_model.derive.page_nav import ReferenceLink
    from fransys_model.kernel import Model


def page_links(model: Model, sheet: SheetRow, links: tuple[ReferenceLink, ...]) -> str:
    """Typst placing one empty linked box per link of a page, in the drawing's own mm.

    The same transform as the drawing's: `grid_to_mm` from the content origin. Nothing prints.
    """
    boxes = []
    per_division = mm_per_division(model, sheet)
    for link in links:
        left = grid_to_mm(sheet.content_x_mm, link.x, per_division)
        top = grid_to_mm(sheet.content_y_mm, link.y, per_division)
        width = grid_to_mm(0, link.width, per_division)
        height = grid_to_mm(0, link.height, per_division)
        body = f"box(width: {width:.3f}mm, height: {height:.3f}mm)"
        boxes.append(
            f"#place(top + left, dx: {left:.3f}mm, dy: {top:.3f}mm, link(<{link.target}>, {body}))"
        )
    return "".join(boxes)
