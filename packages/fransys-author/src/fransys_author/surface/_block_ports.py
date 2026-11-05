"""The ports a series wires on functions that can draw in another block (author-0050)."""

from typing import TYPE_CHECKING

from fransys_author.handles import Port
from fransys_author.surface._pairing import SeriesBridge
from fransys_author.surface._pin_tuple import PinTuple
from fransys_author.surface._strip import TerminalStrip
from fransys_author.surface._supply_rails import _Rails

if TYPE_CHECKING:
    from fransys_author.surface._pairing import Ends


def series_ports(elements: tuple[object, ...], found: list[list[Ends]]) -> tuple[Port, ...]:
    """The ports of the function elements: a pin names no function, so it adds none (API-022 W2)."""
    return tuple(
        end.port
        for element, ends in zip(elements, found, strict=True)
        if not isinstance(element, _Rails | TerminalStrip | SeriesBridge | Port | PinTuple)
        for one in ends
        for end in (*one.line, *one.load)
    )
