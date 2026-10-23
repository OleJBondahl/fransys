"""The ports a series wires on functions that can draw in another block (author-0050)."""

from typing import TYPE_CHECKING

from fransys_author.surface._ends import is_bridge
from fransys_author.surface._strip import TerminalStrip
from fransys_author.surface._supply_rails import _Rails

if TYPE_CHECKING:
    from fransys_author.handles import Port
    from fransys_author.surface._pairing import Ends


def series_ports(elements: tuple[object, ...], found: list[list[Ends]]) -> tuple[Port, ...]:
    """The ports of the plain elements: not a supply or rail, a strip or a cable."""
    return tuple(
        end.port
        for element, ends in zip(elements, found, strict=True)
        if not isinstance(element, _Rails | TerminalStrip) and not is_bridge(element)
        for one in ends
        for end in (*one.line, *one.load)
    )
