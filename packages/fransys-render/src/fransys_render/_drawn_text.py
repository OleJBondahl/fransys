"""One `DrawnText` as a symdef `<text>` tag, placed by symdef's corner rule (render-0024)."""

from decimal import Decimal
from typing import TYPE_CHECKING

import symdef
from symdef import Box, Point

if TYPE_CHECKING:
    from fransys_layout.drawing import DrawnText, Style

__all__ = ["text_tag"]


def text_tag(text: DrawnText, library: symdef.Library, style: Style) -> str:
    """The tag of `text`: font size from the label style's capital height, placed by its corner."""
    label = dict(style.texts)["label"]
    font = library.font
    assert font is not None  # noqa: S101 -- a drawn library carries its font
    ratio = Decimal(font.cap_height) / Decimal(font.units_per_em)
    size_mm = float((Decimal(str(label.height_mm)) / ratio).quantize(Decimal("0.0001")))
    g, m = style.g_per_module, style.module_mm
    b = text.box
    box = Box(Point(b.x / g, b.y / g), Point((b.x + b.w) / g, (b.y + b.h) / g))
    placed = symdef.corner_text(box, text.anchor, size_mm / m, font)
    return symdef.text_tag(
        text.text,
        Point(placed.point.x * m, placed.point.y * m),
        size_mm,
        anchor=placed.anchor,
        font_family=label.family,
        turn=placed.turned,
    )
