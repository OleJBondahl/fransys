"""A symbol's natural size, keepout and table step in grid units: the one home of the arithmetic.

The builder reads it and passes sizes in, so layout's core needs no symdef (SYMDEF-SLOTS SS6).
"""

from dataclasses import dataclass
from typing import Literal

from symdef import body_box, keepout_box

from electrical_symbols._library import LIBRARY
from electrical_symbols.box_ports import G_PER_MODULE

Axis = Literal["x", "y"]

# The symbols that are table rows, with the axis `table()` steps them along.
TABLE_ROW_AXIS: dict[str, Axis] = {
    "pin-cell": "y",
    "pin-cell-wide": "y",
    "cable-column": "x",
    "contact-row": "y",
}


@dataclass(frozen=True)
class Natural:
    """Sizes in G (a G is 0.125 M), base orientation, in the symbol's own coordinates.

    `body` is (width, height) of the body box, leads included. `keepout` is the margin beyond
    that box (left, top, right, bottom) that the slot text boxes need. `step` is the body extent
    along the table axis `axis`, 0 and None for a symbol that is not a table row. `cut_x` and
    `cut_y` are the stretch cuts, None where the symbol has none.
    """

    body: tuple[int, int]
    keepout: tuple[int, int, int, int]
    step: int
    axis: Axis | None
    cut_x: int | None
    cut_y: int | None


def _g(modules: float) -> int:
    return round(modules * G_PER_MODULE)


def natural(key: str) -> Natural:
    """The natural sizes of symbol `key`; `UnknownSymbolError` when the library has no such key."""
    symbol = LIBRARY.get(key)
    body, keep = body_box(symbol), keepout_box(symbol)
    width, height = _g(body.max.x - body.min.x), _g(body.max.y - body.min.y)
    margins = (
        _g(body.min.x - keep.min.x),
        _g(body.min.y - keep.min.y),
        _g(keep.max.x - body.max.x),
        _g(keep.max.y - body.max.y),
    )
    axis = TABLE_ROW_AXIS.get(key)
    step = 0 if axis is None else (width if axis == "x" else height)
    cuts = {s.axis: _g(s.at) for s in symbol.stretch}
    return Natural((width, height), margins, step, axis, cuts.get("x"), cuts.get("y"))
