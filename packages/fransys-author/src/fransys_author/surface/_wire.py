"""The reading of `wire=` and of a pin argument, shared by `d.series` and `d.detail.wire`."""

from collections.abc import Mapping
from decimal import Decimal
from typing import TYPE_CHECKING, NamedTuple

from fransys_author.errors import AuthorError
from fransys_author.handles import Port, Terminal
from fransys_author.surface._bar import take_screw
from fransys_author.surface._carry import refuse_carried
from fransys_author.surface._handles import Fn
from fransys_author.surface._strip import TerminalStrip
from fransys_author.surface._unit_strip import is_unit_strip, take
from fransys_model.vocab import COLOUR_GRAMMAR, split_colour

if TYPE_CHECKING:
    from fransys_author.surface._rows import RowValue, WiringRow
    from fransys_author.wiring import Wiring

    from .design import Design

_TUPLE_LEN = 2

type Colour = str  # an IEC 60757 code from `colours`, such as BU or GNYE
type Spec = tuple[Colour, float]
type WireArg = Spec | tuple[Spec, ...] | float | str | Decimal | Mapping[WiringRow, RowValue] | None


class RowWire(NamedTuple):
    """A `wire=` with no colour of its own: a size or a row table, read per wire from its row."""

    size: Decimal | None
    rows: "Mapping[WiringRow, RowValue] | None"


class PoleWire(NamedTuple):
    """A `wire=` of one `(colour, size)` per pole, in pole order (author-0060)."""

    wirings: "tuple[Wiring, ...]"


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


def _size(mm2: object) -> Decimal:
    size = _gauge(mm2)
    if size <= 0:
        msg = f"wire= size is a positive cross-section in mm2, got {mm2!r}"
        raise AuthorError(msg)
    return size


def _per_pole(design: Design, wire: tuple[object, ...]) -> PoleWire:
    """A tuple of `(colour, mm2)` specs, one per pole; a size or row table among them is refused."""
    for spec in wire:
        if not (isinstance(spec, tuple) and len(spec) == _TUPLE_LEN):
            msg = f"wire= per pole is a tuple of (colour, mm2) specs only, got {spec!r} in {wire!r}"
            raise AuthorError(msg)
    return PoleWire(tuple(wiring_for(design, spec) for spec in wire))


def read_wire(design: Design, wire: WireArg) -> Wiring | RowWire | PoleWire:
    """`wire=` read once: a `(colour, mm2)` is fixed wiring, a tuple of them one per pole."""
    if isinstance(wire, tuple):
        if any(isinstance(spec, tuple) for spec in wire):
            return _per_pole(design, wire)
        return wiring_for(design, wire)
    if wire is None:
        return RowWire(None, None)
    if isinstance(wire, Mapping):
        return RowWire(None, wire)
    if isinstance(wire, int | float | str | Decimal) and not isinstance(wire, bool):
        return RowWire(_size(wire), None)
    msg = (
        "wire= is a size, a table of rows, a (colour, mm2) tuple, or one such tuple per pole, "
        f"got {wire!r}"
    )
    raise AuthorError(msg)


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
