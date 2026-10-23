"""A drawn symbol's body rectangle in G, read from the library (DEL-4 reader tests)."""

from symdef import Orientation, orient_box
from symdef.boxes import body_box

from electrical_symbols import LIBRARY
lazy from fransys_layout.drawing import DrawnSymbol

__all__ = ["Rect", "body_g"]

Rect = tuple[int, int, int, int]


def body_g(symbol: DrawnSymbol) -> Rect:
    """`symbol`'s own body as (x0, y0, x1, y1) in G: the library body turned and moved to it."""
    box = orient_box(body_box(LIBRARY.get(symbol.key)), Orientation(symbol.orient))
    per = LIBRARY.grid.divisions_per_module
    return (
        symbol.x + int(box.min.x * per),
        symbol.y + int(box.min.y * per),
        symbol.x + int(box.max.x * per),
        symbol.y + int(box.max.y * per),
    )
