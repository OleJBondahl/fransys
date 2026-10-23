"""The pen of a cable block: grid to mm, and the toolkit's shapes a block is made of."""

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from symdef import Point, Weight, line_mm, outline_mm, rect_mm, text_tag, wire

from electrical_symbols import sheet_svg

from ._library import font_family, grid_to_mm, text_room_g
from ._numbers import format_decimal, printed_font_mm
from ._symbols import symbol_body

if TYPE_CHECKING:
    from electrical_symbols import Library

type Grid = int | Decimal

_INK = "black"  # cable blocks print black on white
_DASH = "long"  # the dash a by-others box and its cells are drawn with (`[dash]` of the library)


@dataclass(frozen=True)
class Pen:
    """Converts a block's grid positions to mm on its sheet's module, and draws its shapes.

    A block's origin is its own top-left (0, 0), not the sheet's content box. A position may be
    a half grid unit (a cell's middle), so every method takes an `int` or a `Decimal`.
    """

    library: Library
    module_mm: Decimal
    text_height_mm: Decimal
    pad_g: int

    @property
    def font_g(self) -> int:
        """The grid units one text line is given."""
        return text_room_g(self.library, self.text_height_mm, self.module_mm)

    @property
    def font_mm(self) -> Decimal:
        """The printed font size in mm."""
        return printed_font_mm(self.library, self.text_height_mm)

    def mm(self, g: Grid) -> str:
        """`g` grid units as mm, in the shortest decimal form."""
        return format_decimal(grid_to_mm(0, g, self.module_mm))

    def _at(self, g: Grid) -> float:
        return float(grid_to_mm(0, g, self.module_mm))

    def _box(self, box: tuple[Grid, Grid, Grid, Grid]) -> tuple[float, float, float, float]:
        x, y, width, height = box
        return self._at(x), self._at(y), self._at(width), self._at(height)

    def svg(self, width: Grid, height: Grid, body: str) -> str:
        """The `<svg>` of a `width` x `height` block, padded half a stroke so its outline shows."""
        margin = self.library.lines[Weight.NORMAL] / 2
        return sheet_svg(self._at(width), self._at(height), body, margin_mm=margin)

    def rect(self, css: str, box: tuple[Grid, Grid, Grid, Grid], *, dashed: bool) -> str:
        """One `<rect>` of class `symbol` and `css` over `box` (x, y, width, height)."""
        return rect_mm(
            self._box(box),
            library=self.library,
            weight=Weight.NORMAL,
            stroke=_INK,
            fill="none",
            dash=_DASH if dashed else None,
            classes=f"symbol {css}",
        )

    def outline(self, css: str, box: tuple[Grid, Grid, Grid, Grid], *, dashed: bool) -> str:
        """A box's outline: a `rect`, or if dashed four edges drawn left to right and top down.

        Dashes then start at the same corner on facing edges, so they stay in phase (Fix 2).
        """
        return outline_mm(
            self._box(box),
            library=self.library,
            weight=Weight.NORMAL,
            stroke=_INK,
            dash=_DASH if dashed else None,
            classes=f"symbol {css}",
        )

    def line(self, css: str, a: tuple[Grid, Grid], b: tuple[Grid, Grid], *, dashed: bool) -> str:
        """One `<line>` of class `symbol` and `css` from `a` to `b`."""
        return line_mm(
            (self._at(a[0]), self._at(a[1])),
            (self._at(b[0]), self._at(b[1])),
            library=self.library,
            weight=Weight.NORMAL,
            stroke=_INK,
            dash=_DASH if dashed else None,
            classes=f"symbol {css}",
        )

    def wire(self, style_id: str, points: tuple[tuple[Grid, Grid], ...]) -> str:
        """The library wire style `style_id` drawn through `points`."""
        module = self.library.grid.divisions_per_module
        corners = [(float(Decimal(x) / module), float(Decimal(y) / module)) for x, y in points]
        drawn = wire(self.library, style_id, corners)
        return symbol_body(self.library, drawn, self.module_mm, self.font_mm)

    def text(
        self,
        css: str,
        at: tuple[Grid, Grid],
        value: str,
        *,
        middle: bool = False,
        end: bool = False,
    ) -> str:
        """One `<text>` of class `label` and `css` at `at` (x, top); centred on x if `middle`.

        With `end` the text ends at x, so it reads leftward from a point.
        """
        return text_tag(
            value,
            Point(self._at(at[0]), self._at(at[1])),
            float(self.font_mm),
            anchor="middle" if middle else "end" if end else "start",
            font_family=font_family(self.library),
            at="top",
            font=self.library.font,
            classes=f"label {css}",
        )

    def upward_text(self, css: str, at: tuple[Grid, Grid], value: str) -> str:
        """One `<text>` turned to read upward, centred on `at` (x, y): the middle of its extent.

        The turn is about the baseline's midpoint, as the schematic's vertical references are
        (render-0008); the em box then lies half a font either side of x.
        """
        return text_tag(
            value,
            Point(self._at(at[0]), self._at(at[1])),
            float(self.font_mm),
            anchor="middle",
            font_family=font_family(self.library),
            turn=True,
            at="centre",
            font=self.library.font,
            classes=f"label {css}",
        )
