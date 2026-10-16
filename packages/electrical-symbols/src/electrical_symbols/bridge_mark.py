"""The terminal list's Bridge marks from data: `symbols/bridge-line.toml` and `bridge-tick.toml`.

A jumper lane is a vertical line over the rows of its group and a tick on each member row. The
line is one lane wide and is stretched on y by the page that places it, so its pen holds; the
tick keeps its size. This only picks the symbol; a piece's room is the union of its slots' boxes.
"""

from typing import Literal

lazy from symdef import Symbol, slots_box

from electrical_symbols._library import LIBRARY

type BridgePiece = Literal["line", "tick"]


def bridge_mark(piece: BridgePiece) -> Symbol:
    """The Bridge mark symbol of `piece`: a lane's `line` or a row's `tick`."""
    return LIBRARY.get(f"bridge-{piece}")


def bridge_mark_room(piece: BridgePiece) -> tuple[float, float]:
    """`piece`'s width and height in mm: the box of its slots, the room its drawing fills."""
    box = slots_box(bridge_mark(piece))
    return float(box.width), float(box.height)
