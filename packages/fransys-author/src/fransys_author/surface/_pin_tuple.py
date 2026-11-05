"""A pin, or a tuple of one device's pins, as a series element (author-0055 C4, author-0057 C6).

Its pins are both the line and the load ends, so a pin stands at any position of a series.
"""

from typing import TYPE_CHECKING, override

from fransys_author.errors import AuthorError
from fransys_author.handles import Port
from fransys_author.surface._fixed import take
from fransys_author.surface._handles import Fn
from fransys_author.surface._pairing import End, Ends, SeriesElement

if TYPE_CHECKING:
    from fransys_author.surface.design import Design


class PinTuple(SeriesElement):
    """Pins named one by one as one series element, one pin per pole, in the order written.

    Does not read a pin's side: each pin stands as both the line and the load end.
    """

    def __init__(self, pins: tuple[Port, ...]) -> None:
        """Hold `pins`; `pin_tuple` makes these."""
        self._pins = pins

    @override
    def _series_width(self) -> int | None:
        """One pin takes the series' width; several set it."""
        return len(self._pins) if len(self._pins) > 1 else None

    @override
    def _series_ends(self, design: Design, width: int | None) -> Ends:
        for pin in self._pins:
            if pin._terminal is not None:
                take(design, pin._terminal)
        ends = tuple(End(pin, None) for pin in self._pins)
        return Ends(line=ends, load=ends)


def is_lone_pin(element: object) -> bool:
    """Whether `element` is one pin of a function (a terminal's `.inner` or `.outer` is not)."""
    return isinstance(element, Port) and element._terminal is None


def is_mixed_tuple(element: object) -> bool:
    """Whether `element` is a tuple of functions and free pins, with a function among them."""
    return (
        isinstance(element, tuple)
        and any(isinstance(item, Fn) for item in element)
        and all(isinstance(item, Fn) or is_lone_pin(item) for item in element)
    )


def is_pin_tuple(element: object) -> bool:
    """Whether `element` is a non-empty tuple whose items are all pins (no terminal among them)."""
    return isinstance(element, tuple) and bool(element) and all(isinstance(item, Port) for item in element)


def pin_tuple(element: tuple[Port, ...]) -> PinTuple:
    """`element` as a series element; a pin written twice raises, since it would take two poles."""
    if not any(pin._terminal for pin in element):
        _one_device(element)
    ids = [pin.id for pin in element]
    if twice := next((pin for pin in element if ids.count(pin.id) > 1), None):
        msg = f"a tuple in a series names pin {twice.name} twice: one pin is one pole"
        raise AuthorError(msg)
    return PinTuple(element)


def _one_device(pins: tuple[Port, ...]) -> None:
    """Raise when `pins` are on more than one device: a tuple spans the functions of one."""
    owners = {pin.key[0] for pin in pins}
    if len(owners) > 1:
        msg = (
            "a tuple in a series holds the pins of one device, not "
            f"{' and '.join(sorted(owners))}: "
            "name one device's pins in pole order, or wire the others with "
            "d.series(pin, pin, wire=...)"
        )
        raise AuthorError(msg)
