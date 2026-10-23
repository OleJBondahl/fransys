"""The terminal list's Bridge mark pieces: the symbols pdf places in each row's cell (render-0021).

Each piece is one `electrical_symbols` symbol drawn in mm with the table rule's pen. pdf draws no
line: it places these images, and stretches the lane `line` on y only, so its pen holds.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from symdef import Weight

from electrical_symbols import BridgePiece, bridge_mark, bridge_mark_room, sheet_svg
from fransys_model.derive import BRIDGE_PIECE_KEYS, BridgePieceRow
from fransys_model.derive.print_sizes import LINE_RULE_MM

from ._symbols import symbol_body

if TYPE_CHECKING:
    from electrical_symbols import Library

__all__ = ["bridge_pieces"]

_MM = Decimal(1)  # the Bridge symbols are authored in mm: one module is one mm
_RULE = {Weight.NORMAL: float(LINE_RULE_MM), Weight.THICK: float(LINE_RULE_MM)}


def _piece(library: Library, name: BridgePiece) -> BridgePieceRow:
    width, height = bridge_mark_room(name)
    body = symbol_body(library, bridge_mark(name), _MM, _MM, weights_mm=_RULE)
    return BridgePieceRow(
        svg=sheet_svg(width, height, body, margin_mm=0), width_mm=width, height_mm=height
    )


def bridge_pieces(library: Library) -> frozendict[str, BridgePieceRow]:
    """Each Bridge mark piece by `derive.BRIDGE_PIECE_KEYS`: the `line` and the `tick`. Pure."""
    return frozendict(
        {
            BRIDGE_PIECE_KEYS["line"]: _piece(library, "line"),
            BRIDGE_PIECE_KEYS["tick"]: _piece(library, "tick"),
        }
    )
