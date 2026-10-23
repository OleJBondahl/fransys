"""The `PowerSymbol` records of a core layout: one per drawn stand pin (el-0020, SYMBOL-RULES B).

A pin whose port is on a supply, ground or PE net (`derive.stands`) is drawn with the symbol
`electrical_symbols.power_symbol_key` names for its kind. The core placed it as an anchored item
(`placement_anchors`); here its `Anchored` becomes the record.
"""

from typing import TYPE_CHECKING

from electrical_symbols import power_symbol_key
from fransys_model.kernel import make_id
from fransys_model.layout import Orientation, PowerSymbol

from .placement_anchors import stood

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.core import CoreLayout
    from fransys_model.kernel import Model
    from fransys_model.layout import Page

    from .placement_kit import SymbolKit

__all__ = ["power_symbols"]

_KEY = ("layout", "core")


def power_symbols(
    model: Model,
    layout: CoreLayout,
    pages: Mapping[int, Page],
    kit: SymbolKit,
    stamp: str,
) -> tuple[PowerSymbol, ...]:
    """One `PowerSymbol` per drawn stand pin, in kit order: the page of its symbol."""
    anchored = {(a.sym, a.pin): a for a in layout.annotations.anchored}
    placed = {p.sym: p for page in layout.placement.pages for p in page.placed}
    found = []
    for sym_id, name, port, kind in stood(model, kit):
        item = anchored.get((sym_id, name))
        if item is None:
            continue
        pin = next(xy for xy in placed[sym_id].pin_xy if xy.pin == name)
        record_key = (*_KEY, "power_symbol", sym_id, name)
        found.append(
            PowerSymbol(
                id=make_id(PowerSymbol, record_key),
                key=record_key,
                port=port,
                page=pages[item.page].id,
                symbol=power_symbol_key(kind),
                x=item.x,
                y=item.y,
                pin_x=pin.x,
                pin_y=pin.y,
                orientation=Orientation[item.orient],
                produced_by=stamp,
            )
        )
    return tuple(found)
