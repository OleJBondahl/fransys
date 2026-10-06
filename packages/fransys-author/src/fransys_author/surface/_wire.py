"""`d.wire`: one wire, or a daisy chain, built through the engine's wiring (spec A6)."""

from decimal import Decimal
from typing import TYPE_CHECKING

from fransys_author.errors import AuthorError
from fransys_author.handles import Port, Terminal
from fransys_author.surface._strip import TerminalStrip
from fransys_model.vocab import COLOUR_GRAMMAR, split_colour

if TYPE_CHECKING:
    from fransys_author.wiring import Wiring

    from .design import Design

_MINIMUM_PINS = 2
_TUPLE_LEN = 2

type Colour = str  # an IEC 60757 code from `colours`, such as BU or GNYE


def _gauge(mm2: object) -> Decimal:
    if isinstance(mm2, float):
        return Decimal(str(mm2))
    if isinstance(mm2, int | str | Decimal) and not isinstance(mm2, bool):
        return Decimal(mm2)
    msg = f"d.wire mm2 is an int, str, Decimal or float, got {mm2!r}"
    raise AuthorError(msg)


def _colour(colour: object) -> str:
    if not isinstance(colour, str) or not colour or split_colour(colour) is None:
        msg = f"d.wire colour {colour!r} is not allowed; use {COLOUR_GRAMMAR}"
        raise AuthorError(msg)
    return colour


def wiring_for(design: Design, wire: object) -> Wiring:
    """The engine wiring for `wire=(colour, mm2)`; the one reading of that argument."""
    if not (isinstance(wire, tuple) and len(wire) == _TUPLE_LEN):
        msg = f"d.wire wire= is a (colour, mm2) tuple, got {wire!r}"
        raise AuthorError(msg)
    return design._engine.wiring(colour=_colour(wire[0]), gauge=_gauge(wire[1]))


def _port(pin: object) -> Port:
    if isinstance(pin, TerminalStrip):
        pin = pin._take(1)[0]  # the step `d.series` takes: the strip's next free terminal
    if isinstance(pin, Terminal):
        return pin.inner
    if isinstance(pin, Port):
        return pin
    msg = f"d.wire joins pins: name one pin, got {type(pin).__name__}"
    raise AuthorError(msg)


class Wires:
    """The `wire` call of the surface `Design`."""

    def wire(
        self: "Design",
        *pins: Port | Terminal | TerminalStrip,
        wire: tuple[Colour, float],
        label: str | None = None,
        n: int | None = None,
    ) -> None:
        """Wire the pins: two make one wire, more make a daisy chain, one wire per pair.

        Does not pick a wire or find pins; a terminal lands on its inner side.
        A strip or run as a pin stands for its next free terminal, each place it appears.
        """
        if len(pins) < _MINIMUM_PINS:
            msg = f"d.wire joins at least {_MINIMUM_PINS} pins, got {len(pins)}"
            raise AuthorError(msg)
        ports = [_port(pin) for pin in pins]
        wiring_for(self, wire).run(*ports, n=n, label=label)
