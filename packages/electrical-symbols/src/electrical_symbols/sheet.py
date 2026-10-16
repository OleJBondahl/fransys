"""The sheet frame from data: the border and the four reference strips, stretched by symdef.

The symbols are `symbols/sheet-frame.toml` and `sheet-strip-<side>.toml`, authored in mm; the
renderer draws them with `to_fragment_mm(module_mm=1.0)`. These functions only pass the caller's
values to `stretch`, `table` and `translate`.
"""

from typing import Literal

from symdef import Symbol, slot_box, stretch, table, translate

from electrical_symbols._library import LIBRARY

type Corner = tuple[float, float]  # where a part's top-left corner goes on the sheet, in mm


def sized(key: str, width: float, height: float) -> Symbol:
    """The library symbol `key` stretched to `width` by `height` mm."""
    return stretch(stretch(LIBRARY.get(key), "x", width), "y", height)


def frame_border(corner: Corner, width: float, height: float) -> Symbol:
    """The frame border, `width` by `height` mm, with its top-left at `corner`."""
    return translate(sized("sheet-frame", width, height), *corner)


def frame_strip(
    side: str, corner: Corner, cell: tuple[float, float], count: int, axis: Literal["x", "y"]
) -> Symbol:
    """One reference strip: `count` cells of `side`'s cell, each `cell` mm, along `axis`.

    Cell k's label slot is `<k>.label`; a tick stands between two cells, none at the strip's ends.
    """
    row = sized(f"sheet-strip-{side}", *cell)
    return translate(table(row, count, axis), *corner)


def slot_box_mm(symbol: Symbol, slot: str) -> tuple[float, float, float, float]:
    """The slot's box as x, y, width and height in mm; `KeyError` names the symbol and the slot."""
    for one in symbol.slots:
        if one.id == slot:
            box = slot_box(one)
            return box.min.x, box.min.y, box.max.x - box.min.x, box.max.y - box.min.y
    msg = f"symbol {symbol.name!r} has no slot {slot!r}"
    raise KeyError(msg)


def slot_room(symbol: Symbol, slot: str) -> tuple[float, float]:
    """The slot's room as width and height in mm; `KeyError` names the symbol and the slot."""
    _, _, width, height = slot_box_mm(symbol, slot)
    return width, height


def slot_widths(symbol: Symbol) -> dict[str, float]:
    """The width in mm of every slot of `symbol`, by slot id."""
    return {one.id: slot_room(symbol, one.id)[0] for one in symbol.slots}
