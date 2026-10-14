"""A cable block's elements in the order a reader reads them (render-0011).

Typst keeps the SVG's element order in the PDF, so that order is the text layer's. Shapes come
first; texts follow row by row, each row left to right. No shape is filled, so painting the
texts last changes no pixel.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._cable_pen import Grid, Pen


class Ink:
    """The shapes and the texts of one block, collected as the block is drawn."""

    def __init__(self, pen: Pen) -> None:
        self.pen = pen
        self._shapes: list[str] = []
        self._texts: list[tuple[Grid, Grid, str]] = []

    def shape(self, svg: str) -> None:
        """Add a rect, line or polyline; shapes keep the order they are added in."""
        self._shapes.append(svg)

    def text(self, css: str, at: tuple[Grid, Grid], value: str, *, middle: bool = False) -> None:
        """Add a level text at `at` (x, top); its row is the line's middle."""
        row = at[1] + Decimal(self.pen.font_g) / 2
        self._texts.append((row, at[0], self.pen.text(css, at, value, middle=middle)))

    def upward_text(self, css: str, at: tuple[Grid, Grid], value: str) -> None:
        """Add a text turned to read upward, centred on `at`; its row is `at`'s y."""
        self._texts.append((at[1], at[0], self.pen.upward_text(css, at, value)))

    def body(self) -> str:
        """Every shape, then the texts by row and then by x."""
        texts = sorted(self._texts, key=lambda t: (t[0], t[1]))
        return "".join(self._shapes) + "".join(svg for _, _, svg in texts)
