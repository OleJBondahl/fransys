"""The house label's em in G (CORE-TEXTS A, model-0319; layout-0385)."""

from typing import TYPE_CHECKING

from fransys_model.derive import text_room_g
from fransys_model.derive.print_sizes import house_text_height_mm

if TYPE_CHECKING:
    from fransys_model.kernel import Model
    from fransys_model.layout import SheetFormat

__all__ = ["label_height"]


def label_height(model: Model, sheet: SheetFormat) -> int:
    """The em, in G, of the house label: its capital height over the font's ratio (E10).

    `text_width` takes an em, so the capital height is converted once, by `text_room_g`.
    """
    return text_room_g(model, house_text_height_mm(model), sheet)
