"""The invisible links over a drawing: each cross reference opens the partner's sheet (NV1, NV2)."""

from typing import TYPE_CHECKING

from fransys_model.derive.grid_mm import grid_to_mm
from fransys_model.derive.page_nav import reference_links

if TYPE_CHECKING:
    from collections.abc import Collection

    from fransys_model.derive import PageId, SheetRow
    from fransys_model.kernel import Model


def page_links(model: Model, page: PageId, sheet: SheetRow, known: Collection[PageId]) -> str:
    """Typst placing one empty linked box per reference on `page`, in the drawing's own mm.

    The same transform as the drawing's: `grid_to_mm` from the content origin. Nothing prints.
    """
    boxes = []
    for link in reference_links(model, page, known):
        left = grid_to_mm(sheet.content_x_mm, link.x, sheet.module_mm)
        top = grid_to_mm(sheet.content_y_mm, link.y, sheet.module_mm)
        width = grid_to_mm(0, link.width, sheet.module_mm)
        height = grid_to_mm(0, link.height, sheet.module_mm)
        body = f"box(width: {width:.3f}mm, height: {height:.3f}mm)"
        boxes.append(
            f"#place(top + left, dx: {left:.3f}mm, dy: {top:.3f}mm, link(<{link.target}>, {body}))"
        )
    return "".join(boxes)
