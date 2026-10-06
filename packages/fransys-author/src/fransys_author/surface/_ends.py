"""What each kind of series element offers: its ends, its width, and the `Parallel` handle (EA5)."""

from typing import TYPE_CHECKING, Any, Protocol, TypeGuard, cast

from fransys_author.errors import AuthorError
from fransys_author.handles import Port, Terminal
from fransys_author.surface._carrier import carrier_function
from fransys_author.surface._device import Device
from fransys_author.surface._handles import Fn
from fransys_author.surface._pairing import Ends, SeriesElement, ends_of, poles

if TYPE_CHECKING:
    from .design import Design

_PIN = "a pin is one wire: use d.wire"
_ALLOWED = "a device, a function, a supply or rail, a terminal strip, a cable or a parallel"


class SeriesBridge(Protocol):
    """A cable-like element that lands between its two neighbours instead of being wired to them.

    Does not get wired by the series: it is handed each neighbour and its ends.
    """

    def _series_between(
        self, design: Design, before: tuple[object, Ends], after: tuple[object, Ends]
    ) -> None: ...

    def _series_width(self) -> None: ...


class Parallel:
    """Members sharing one place in a series, each from the previous load to the next line.

    Does not connect anything by itself: the series wires its members.
    """

    def __init__(self, members: tuple[object, ...]) -> None:
        """Hold `members`; `d.parallel` makes these."""
        self._members = members

    def _series_width(self) -> None:
        return None

    def _branches(self, design: Design, width: int | None) -> list[Ends]:
        return [end for member in self._members for end in branches(design, member, width)]

    def _series_ends(self, design: Design, width: int | None) -> Ends:
        """The first member's ends; the series reads every member through `branches`."""
        return self._branches(design, width)[0]


def _fn_ends(design: Design, fn: Fn) -> Ends:
    ends = ends_of(design._pairing_facts, fn._fn)
    if not ends.line:
        msg = f"{fn._label}.{fn._fn.name} has no poles: name its pins"
        raise AuthorError(msg)
    return ends


def _device_ends(design: Design, device: Device, width: int | None) -> Ends:
    """The ends of the one function of `device` that has `width` poles."""
    facts = design._pairing_facts
    fn = carrier_function(
        list(device._item.functions), lambda f: len(poles(facts, f)), width, device._label
    )
    return ends_of(facts, fn)


def _ends_for(design: Design, element: object, width: int | None) -> Ends:
    if isinstance(element, Port | Terminal):
        raise AuthorError(_PIN)
    if isinstance(element, Fn):
        return _fn_ends(design, element)
    if isinstance(element, Device):
        return _device_ends(design, element, width)
    if not isinstance(element, SeriesElement):
        msg = f"a series takes {_ALLOWED}, not {type(element).__name__}"
        raise AuthorError(msg)
    return element._series_ends(design, width)


def branches(design: Design, element: object, width: int | None) -> list[Ends]:
    """The ends of `element` at `width`: one set, or one per member of a `Parallel`."""
    if isinstance(element, Parallel):
        return element._branches(design, width)
    return [_ends_for(design, element, width)]


def width_of(design: Design, element: object) -> int | None:
    """The width `element` sets for its series, `None` when it sets none."""
    if isinstance(element, Fn):
        return len(_fn_ends(design, element).line)
    probe: Any = getattr(element, "_series_width", None)
    return None if probe is None else cast("int | None", probe())


def is_bridge(element: object) -> TypeGuard[SeriesBridge]:
    """True for an element that lands between its neighbours (`SeriesBridge`)."""
    return hasattr(element, "_series_between")
