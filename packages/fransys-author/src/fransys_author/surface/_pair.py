"""Surface mixin for `pair`: a cable joins two ends pin for pin, with no line/load direction."""

from typing import TYPE_CHECKING, cast

from fransys_author.errors import AuthorError
from fransys_author.handles import Port, Terminal
from fransys_author.surface._cable import Cable
from fransys_author.surface._fixed import FixedTerminals, fixed
from fransys_author.surface._handles import Fn
from fransys_author.surface._pairing import End, Ends
from fransys_author.surface._pin_tuple import is_pin_tuple, pin_tuple

if TYPE_CHECKING:
    from .design import Design

_HOW = (
    "name its pins: `x8[1:3]` or `x8[1]` for terminals, `b1.sig` for a function, "
    "`b1.sig[1]` for a pin, `(b1.sig[1], b1.sig[2])` or `b1.sig.pins[:2]` for a tuple of pins"
)


def _held(end: object) -> FixedTerminals | None:
    """`end` as fixed terminals (`x8[1:3]`, one terminal, a tuple of terminals), else `None`."""
    if isinstance(end, FixedTerminals):
        return end
    if isinstance(end, Terminal) or (
        isinstance(end, tuple) and end and all(isinstance(t, Terminal) for t in end)
    ):
        return fixed(end)
    return None


def _pins(design: Design, end: object) -> tuple[Port, ...]:
    """The pins `end` offers in order: a function's `Fn.pins`, a terminal's field side."""
    if isinstance(end, Fn):
        return end.pins
    if isinstance(end, Port) or is_pin_tuple(end):
        pins = cast("tuple[Port, ...]", end if isinstance(end, tuple) else (end,))
        return tuple(e.port for e in pin_tuple(pins)._series_ends(design, None).load)
    if (held := _held(end)) is not None:
        return tuple(e.port for e in held._series_ends(design, None).load)
    msg = (
        f"d.pair takes terminals, a function or pins at each end, not {type(end).__name__}: {_HOW}"
    )
    raise AuthorError(msg)


class Pairs:
    """The `pair` call of `Design`."""

    def pair(self: "Design", a: object, cable: Cable, b: object) -> None:  # noqa: UP037 -- Design imports this module: unquoted, inspect.signature raises NameError
        """Join `a` to `b` through `cable`, pin for pin: core i joins `a`'s pin i to `b`'s pin i.

        An end is terminals (`x8[1:3]`), a function (`b1.sig`) or pins (`b1.sig.pins[:2]`).
        Does not read a side, take `wire=`, or accept a strip or a device.
        """
        if not isinstance(cable, Cable):
            msg = (
                f"d.pair(a, cable, b) takes a cable in the middle, not {type(cable).__name__}: "
                "add one with d.cable(...), or use d.series for other elements"
            )
            raise AuthorError(msg)
        first, last = _pins(self, a), _pins(self, b)
        cable._series_between(
            self,
            (a, Ends((), tuple(End(p, None) for p in first))),
            (b, Ends(tuple(End(p, None) for p in last), ())),
            "d.pair",
        )
