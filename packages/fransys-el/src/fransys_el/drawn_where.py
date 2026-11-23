"""The ports whose placements each draw a where-text naming the other (R1396, R1397).

A terminal placed more than once prints under each tag where every other placement is, one line each. That text is a drawn join, like a
reference pair: it is compared by recomputing `position_at` for the other placement's page and cell, never by
reading the printed string.
"""

from typing import TYPE_CHECKING

from fransys_model.derive import (
    cell_destination,
    drawn_stands,
    far_pins,
    function_placements,
    function_ports,
    port_function,
    position_at,
    rail_drawn_by,
)
from fransys_model.derive.page_nav import same_pdf
from fransys_model.layout import FrameCell, Page, layout_of

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Function, Port

    from .drawn_netlist import Netlist

__all__ = ["stand_places", "where_joined", "where_link", "where_named", "where_targets", "where_text"]

type _Place = tuple[Id[Page], FrameCell]


def where_text(model: Model, here: _Place, there: _Place) -> str:
    """The where-text of the placement `here`: where `there` is, read from `here`'s page (R1397)."""
    pages = layout_of(model, Page)
    return position_at(model, pages[here[0]], pages[there[0]], there[1].column, there[1].row)


def stand_places(model: Model, function: Id[Function]) -> tuple[tuple[Id[Port], _Place], ...]:
    """Each stand pin, with its device's place, that a rail terminal's own conductors reach: the power symbol its replica stands for (R2993).

    A rail terminal drawn as a replica names where its symbol stands; the boundary wire's far end is no stand, so it gives none.
    """
    ports = function_ports(model, function)
    if not rail_drawn_by(model).keys() & set(ports):
        return ()
    rows, stood = function_placements(model), drawn_stands(model)
    return tuple((far, place) for _, far in far_pins(model, ports) if far in stood for place in rows.get(port_function(model, far), ()))


def where_targets(model: Model, function: Id[Function], rows: Sequence[_Place], page: Id[Page]) -> tuple[_Place, ...]:
    """The places a terminal's tag on `page` names under it: each other placement of `rows` and each stand it names, once (R1397, R2993)."""
    return tuple(dict.fromkeys((*(r for r in rows if r[0] != page), *(at for _, at in stand_places(model, function)))))


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


def where_named(model: Model, net: Netlist) -> set[tuple[str, str]]:
    """The `(port, far)` ends of a rail terminal's replica whose every far stand's position is printed under its tag (R2993)."""
    found = set()
    for port, owner in net.owners.items():
        function = port_function(model, net.ids[port])
        stands = () if function is None else stand_places(model, function)
        if stands and all(_names(model, net, owner, here, there) for here in function_placements(model).get(function, ()) for _, there in stands):
            found.update((port, far.value) for far, _ in stands)
    return found


def _names(model: Model, net: Netlist, owner: str, here: _Place, there: _Place) -> bool:
    """True when the symbol `owner` draws, on the page of `here`, the position of `there`."""
    part = net.pages.get(here[0])
    wanted = where_text(model, here, there)
    return part is not None and any(t.owner == owner and t.text == wanted for t in part.drawing.texts)
