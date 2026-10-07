"""The pen of a cable block: grid to mm, and the SVG elements a block is made of (CD8)."""

from dataclasses import dataclass
from decimal import Decimal
from xml.sax.saxutils import escape

from ._constants import ASCENT_RATIO, OUTLINE_DASH_GAP_MM, OUTLINE_DASH_LONG_MM, STROKE_WIDTH_MM
from ._numbers import format_decimal, grid_to_mm

type Grid = int | Decimal

_DASH = (
    f' stroke-dasharray="{format_decimal(OUTLINE_DASH_LONG_MM)},'
    f'{format_decimal(OUTLINE_DASH_GAP_MM)}"'
)


@dataclass(frozen=True)
class Pen:
    """Converts a block's grid positions to mm on its sheet's module, and writes its elements.

    A block's origin is its own top-left (0, 0), not the sheet's content box. A position may be
    a half grid unit (a cell's middle), so every method takes an `int` or a `Decimal`.
    """

    module_mm: Decimal
    font_g: int
    pad_g: int

    def mm(self, g: Grid) -> str:
        """`g` grid units as mm, in the shortest decimal form."""
        return format_decimal(grid_to_mm(0, g, self.module_mm))

    def svg(self, width: Grid, height: Grid, body: str) -> str:
        """The `<svg>` of a `width` x `height` block, padded half a stroke so its outline shows."""
        margin = STROKE_WIDTH_MM / 2
        w = format_decimal(Decimal(self.mm(width)) + 2 * margin)
        h = format_decimal(Decimal(self.mm(height)) + 2 * margin)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}mm" height="{h}mm" '
            f'viewBox="{format_decimal(-margin)} {format_decimal(-margin)} {w} {h}">{body}</svg>'
        )

    def rect(self, css: str, box: tuple[Grid, Grid, Grid, Grid], *, dashed: bool) -> str:
        """One `<rect>` of class `symbol` and `css` over `box` (x, y, width, height)."""
        x, y, width, height = box
        return (
            f'<rect class="symbol {css}" x="{self.mm(x)}" y="{self.mm(y)}" '
            f'width="{self.mm(width)}" height="{self.mm(height)}"{_DASH if dashed else ""}/>'
        )

    def outline(self, css: str, box: tuple[Grid, Grid, Grid, Grid], *, dashed: bool) -> str:
        """A box's outline: a `rect`, or if dashed four edges drawn left to right and top down.

        Dashes then start at the same corner on facing edges, so they stay in phase (Fix 2).
        """
        if not dashed:
            return self.rect(css, box, dashed=False)
        x, y, width, height = box
        edges = (((x, y), (x + width, y)), ((x, y + height), (x + width, y + height)))
        edges += (((x, y), (x, y + height)), ((x + width, y), (x + width, y + height)))
        return "".join(self.line(css, a, b, dashed=True) for a, b in edges)

    def line(self, css: str, a: tuple[Grid, Grid], b: tuple[Grid, Grid], *, dashed: bool) -> str:
        """One `<line>` of class `symbol` and `css` from `a` to `b`."""
        return (
            f'<line class="symbol {css}" x1="{self.mm(a[0])}" y1="{self.mm(a[1])}" '
            f'x2="{self.mm(b[0])}" y2="{self.mm(b[1])}"{_DASH if dashed else ""}/>'
        )

    def polyline(self, css: str, points: tuple[tuple[Grid, Grid], ...]) -> str:
        """One `<polyline>` of class `wire` and `css` through `points`."""
        text = " ".join(f"{self.mm(x)},{self.mm(y)}" for x, y in points)
        return f'<polyline class="wire {css}" points="{text}"/>'

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
        x, top = at
        font_mm = grid_to_mm(0, self.font_g, self.module_mm)
        baseline = grid_to_mm(0, top, self.module_mm) + font_mm * ASCENT_RATIO
        anchor = ' text-anchor="middle"' if middle else ' text-anchor="end"' if end else ""
        return (
            f'<text class="label {css}" x="{self.mm(x)}" y="{format_decimal(baseline)}" '
            f'font-size="{format_decimal(font_mm)}"{anchor}>{escape(value)}</text>'
        )

    def upward_text(self, css: str, at: tuple[Grid, Grid], value: str) -> str:
        """One `<text>` turned to read upward, centred on `at` (x, y): the middle of its extent.

        The turn is about the baseline's midpoint, as the schematic's vertical references are
        (render-0008); the em box then lies half a font either side of x.
        """
        font_mm = grid_to_mm(0, self.font_g, self.module_mm)
        x = grid_to_mm(0, at[0], self.module_mm) - font_mm / 2 + font_mm * ASCENT_RATIO
        sx, sy = format_decimal(x), self.mm(at[1])
        return (
            f'<text class="label {css}" text-anchor="middle" transform="rotate(-90 {sx} {sy})" '
            f'x="{sx}" y="{sy}" font-size="{format_decimal(font_mm)}">{escape(value)}</text>'
        )
