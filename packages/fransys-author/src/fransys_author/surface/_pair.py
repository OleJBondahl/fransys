"""Surface mixin for `pair`: a cable joins two ends pin for pin, with no line/load direction."""

from typing import TYPE_CHECKING

from fransys_author.errors import AuthorError
from fransys_author.handles import Terminal
from fransys_author.surface._cable import Cable
from fransys_author.surface._fixed import FixedTerminals, fixed
from fransys_author.surface._handles import Fn
from fransys_author.surface._pairing import End, Ends

if TYPE_CHECKING:
    from fransys_author.handles import Port

    from .design import Design

_HOW = "name its pins: `x8[1:3]` for terminals, `b1.sig` for a function"


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
    if (held := _held(end)) is not None:
        return tuple(e.port for e in held._series_ends(design, None).load)
    msg = f"d.pair takes terminals or a function at each end, not {type(end).__name__}: {_HOW}"
    raise AuthorError(msg)


class Pairs:
    """The `pair` call of `Design`."""

    def pair(self: "Design", a: object, cable: Cable, b: object) -> None:  # noqa: UP037 -- Design imports this module: unquoted, inspect.signature raises NameError
        """Join `a` to `b` through `cable`, pin for pin: core i joins `a`'s pin i to `b`'s pin i.

        An end is terminals (`x8[1:3]`) or a function (`b1.sig`, pins in connector order).
        Does not read a side, take `wire=`, or accept a strip, a bare port or a device.
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
