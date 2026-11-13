"""The ports whose placements each draw a where-text naming the other (R1396, R1397).

A terminal placed more than once prints under each tag where every other placement is, one line each. That text is a drawn join, like a
reference pair: it is compared by recomputing `position_at` for the other placement's page and cell, never by
reading the printed string.
"""

from typing import TYPE_CHECKING

from fransys_model.derive import cell_destination, function_placements, port_function, position_at
from fransys_model.derive.page_nav import same_pdf
from fransys_model.layout import FrameCell, Page, layout_of

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model

    from .drawn_netlist import Netlist

__all__ = ["where_joined", "where_link", "where_text"]

type _Place = tuple[Id[Page], FrameCell]


def where_text(model: Model, here: _Place, there: _Place) -> str:
    """The where-text of the placement `here`: where `there` is, read from `here`'s page (R1397)."""
    pages = layout_of(model, Page)
    return position_at(model, pages[here[0]], pages[there[0]], there[1].column, there[1].row)


def where_link(model: Model, here: _Place, there: _Place) -> str | None:
    """The destination label of the cell of `there`, or `None` when `there` is outside the PDF that prints `here` (PDF-LINKS R1, R3)."""
    pages = layout_of(model, Page)
    if not same_pdf(model, pages[here[0]], pages[there[0]], None):
        return None
    return cell_destination(model, pages[there[0]], there[1])


def where_joined(model: Model, net: Netlist) -> set[str]:
    """The ports of two placements that each own a text equal to `where_text` of the other placement."""
    rows = function_placements(model)
    found = set()
    for port, owner in net.owners.items():
        function = port_function(model, net.ids[port])
        both = rows.get(function, []) if function is not None else []
        if len(both) > 1 and all(_names(model, net, owner, here, there) for here in both for there in both if there[0] != here[0]):
            found.add(port)
    return found


def _names(model: Model, net: Netlist, owner: str, here: _Place, there: _Place) -> bool:
    """True when the symbol `owner` draws, on the page of `here`, the position of `there`."""
    part = net.pages.get(here[0])
    wanted = where_text(model, here, there)
    return part is not None and any(t.owner == owner and t.text == wanted for t in part.drawing.texts)
