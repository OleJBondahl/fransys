"""The terminal list's Bridge marks from data: `symbols/bridge-line.toml` and `bridge-tick.toml`.

A jumper lane is a vertical line over the rows of its group and a tick on each member row. The
line is one lane wide and is stretched on y by the page that places it, so its pen holds; the
tick keeps its size. This only picks the symbol; a piece's room is the union of its slots' boxes.
"""

from typing import Literal

lazy from symdef import Symbol

from electrical_symbols._library import LIBRARY
from electrical_symbols.sheet import slot_box_mm

type BridgePiece = Literal["line", "tick"]


def bridge_mark(piece: BridgePiece) -> Symbol:
    """The Bridge mark symbol of `piece`: a lane's `line` or a row's `tick`."""
    return LIBRARY.get(f"bridge-{piece}")


def bridge_mark_room(piece: BridgePiece) -> tuple[float, float]:
    """`piece`'s width and height in mm: the union of its slot boxes, the room its drawing fills."""
    boxes = [slot_box_mm(symbol, one.id) for symbol in [bridge_mark(piece)] for one in symbol.slots]
    left = min(x for x, _, _, _ in boxes)
    top = min(y for _, y, _, _ in boxes)
    right = max(x + width for x, _, width, _ in boxes)
    bottom = max(y + height for _, y, _, height in boxes)
    return right - left, bottom - top
