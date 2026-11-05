"""The text of the build's library: the one measure of drawn text and the text height in G (SB11, SIZES, R850).

The width is symdef's, in whole grid units (CC1, model-0373). The height is library data, the library's fixed heights,
written into the model's drawing library record by the facade; no profile sets it. The smallest height is the label's.
"""

import math
from dataclasses import replace
from typing import TYPE_CHECKING

from symdef import text_divisions
from symdef import text_width as symdef_text_width

from fransys_model.derive.print_sizes import TextRole, role_height_mm

if TYPE_CHECKING:
    from symdef import FontMetrics

    from fransys_model.kernel import Model
    from fransys_model.layout import SheetFormat

    from .shape import SymbolLibrary

__all__ = ("text_room_on", "text_width_g")


def text_width_g(font: FontMetrics | None, text: str, *, height: int) -> int:
    """Width of `text` set `height` grid units high in `font`, rounded up to the grid."""
    return math.ceil(round(symdef_text_width(font, text, height), 9))


def text_room_on(model: Model, sheet: SheetFormat, library: SymbolLibrary) -> int:
    """The grid units a text line gets on `sheet`: the library's smallest height over one G, up."""
    grid = replace(library.grid, module_mm=float(sheet.module_mm))
    return text_divisions(grid, library.font, float(role_height_mm(model, TextRole.LABEL)))
