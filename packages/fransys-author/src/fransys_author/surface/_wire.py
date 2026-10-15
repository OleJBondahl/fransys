"""The reading of `wire=` and of a pin argument, shared by `d.series` and `d.detail.wire`."""

from decimal import Decimal
from typing import TYPE_CHECKING

from fransys_author.errors import AuthorError
from fransys_author.handles import Port, Terminal
from fransys_author.surface._bar import take_screw
from fransys_author.surface._carry import refuse_carried
from fransys_author.surface._handles import Fn
from fransys_author.surface._strip import TerminalStrip
from fransys_author.surface._unit_strip import is_unit_strip, take
from fransys_model.vocab import COLOUR_GRAMMAR, split_colour

if TYPE_CHECKING:
    from fransys_author.wiring import Wiring

    from .design import Design

_TUPLE_LEN = 2

type Colour = str  # an IEC 60757 code from `colours`, such as BU or GNYE


def _gauge(mm2: object) -> Decimal:
    if isinstance(mm2, float):
        return Decimal(str(mm2))
    if isinstance(mm2, int | str | Decimal) and not isinstance(mm2, bool):
        return Decimal(mm2)
    msg = f"wire= mm2 is an int, str, Decimal or float, got {mm2!r}"
    raise AuthorError(msg)


def _colour(colour: object) -> str:
    if not isinstance(colour, str) or not colour or split_colour(colour) is None:
        msg = f"wire= colour {colour!r} is not allowed; use {COLOUR_GRAMMAR}"
        raise AuthorError(msg)
    return colour


def wiring_for(design: Design, wire: object) -> Wiring:
    """The engine wiring for `wire=(colour, mm2)`; the one reading of that argument."""
    if not (isinstance(wire, tuple) and len(wire) == _TUPLE_LEN):
        msg = f"wire= is a (colour, mm2) tuple, got {wire!r}"
        raise AuthorError(msg)
    return design._engine.wiring(colour=_colour(wire[0]), gauge=_gauge(wire[1]))


def _port(design: Design, pin: object) -> Port:
    """The port a pin argument stands for; a nested unit's terminal is its outer side (0023)."""
    if isinstance(pin, TerminalStrip):
        pin = pin._take(1)[0]  # the step `d.series` takes: the strip's next free terminal
    if isinstance(pin, Terminal):
        return pin.outer if is_unit_strip(pin, design) else pin.inner
    if isinstance(pin, Port):
        return pin
    msg = f"a pin argument is one pin: name one pin, got {type(pin).__name__}"
    raise AuthorError(msg)


def _wire_port(design: Design, pin: object) -> Port:
    """`_port`, but a unit's strip gives the next free boundary terminal's outer side (0023)."""
    if isinstance(pin, Fn):
        return take_screw(design, pin)  # PE-BAR B2: d.detail.wire only, never a net or a link
    if isinstance(pin, TerminalStrip) and is_unit_strip(pin, design):
        return take(pin, design, 1)[0].outer
    port = _port(design, pin)
    refuse_carried(design, (port,))
    return port
