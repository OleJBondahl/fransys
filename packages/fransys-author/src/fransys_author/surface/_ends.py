"""What each kind of series element offers: its ends, its width, and the `Parallel` handle."""

from typing import TYPE_CHECKING, Any, Protocol, TypeGuard, cast

from fransys_author.errors import AuthorError
from fransys_author.handles import Port, Terminal
from fransys_author.surface._carrier import carrier_function
from fransys_author.surface._device import Device
from fransys_author.surface._fixed import fixed, side_ends
from fransys_author.surface._handles import Fn
from fransys_author.surface._pairing import End, Ends, SeriesElement, ends_of, poles
from fransys_author.surface._partless_end import box_ends
from fransys_author.surface._pin_tuple import is_mixed_tuple, is_pin_tuple, pin_tuple
from fransys_author.surface._throws import whole_changeover
from fransys_model.vocab import FunctionKind

if TYPE_CHECKING:
    from .design import Design

_ALLOWED = (
    "a device, a function, a pin or a tuple of pins, a supply or rail, a terminal strip, "
    "fixed terminals (x1[3], x1[1:4]), a cable or a parallel"
)


class SeriesBridge(Protocol):
    """A cable-like element that lands between its two neighbours instead of being wired to them.

    Does not get wired by the series: it is handed each neighbour and its ends.
    """

    def _series_between(
        self, design: Design, before: tuple[object, Ends], after: tuple[object, Ends], series: str
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
    if fn._fn.kind is FunctionKind.CONTACT_CO:
        raise whole_changeover(fn._label, fn._fn)
    ends = ends_of(design._pairing_facts, fn._fn, partless_ok=True)
    if not ends.line:
        where = f"{fn._label}.{fn._fn.name}"
        msg = (
            f"{where} has no line/load pole pair, so a bare function end cannot pair its pins by "
            f"position: name them with `{where.lower()}.pins` (connector order, or a slice of "
            f"it), or wire them with d.detail.wire(pin, pin, wire=...)"
        )
        raise AuthorError(msg)
    return ends


def _mixed_ends(design: Design, items: tuple[Fn | Port, ...]) -> Ends:
    """The ends of `(L, N)`: a one-pole function gives its pole pair, a pin stands as both."""
    found = [_one_pole(design, item) if isinstance(item, Fn) else _pin(item) for item in items]
    return Ends(tuple(e.line[0] for e in found), tuple(e.load[0] for e in found))


def _pin(pin: Port) -> Ends:
    end = (End(pin, None),)
    return Ends(end, end)


def _one_pole(design: Design, fn: Fn) -> Ends:
    ends = _fn_ends(design, fn)
    if len(ends.line) != 1:
        where = f"{fn._label}.{fn._fn.name}"
        msg = (
            f"a tuple in a series takes one-pole functions and pins; {where} has "
            f"{len(ends.line)} poles: put it alone, or name its poles with {where.lower()}.pole(n)"
        )
        raise AuthorError(msg)
    return ends


def _device_ends(design: Design, device: Device, width: int | None) -> Ends:
    """The ends of the one function of `device` that has `width` poles."""
    facts = design._pairing_facts
    if all(facts.partless(f) for f in device._item.functions):
        return box_ends(facts, device._label, list(device._item.functions), width)
    fn = carrier_function(
        list(device._item.functions), lambda f: len(poles(facts, f)), width, device._label
    )
    return ends_of(facts, fn)


def _tuple_ends(design: Design, element: Terminal | tuple[Any, ...], width: int | None) -> Ends:
    """The ends of a terminal or a tuple: pins, functions and pins, or fixed terminals."""
    if is_pin_tuple(element):
        return pin_tuple(cast("tuple[Port, ...]", element))._series_ends(design, width)
    if is_mixed_tuple(element):
        return _mixed_ends(design, cast("tuple[Fn | Port, ...]", element))
    return fixed(element)._series_ends(design, width)


def _ends_for(design: Design, element: object, width: int | None) -> Ends:
    if isinstance(element, Port):
        return side_ends(design, element) or pin_tuple((element,))._series_ends(design, width)
    if isinstance(element, Terminal | tuple):
        return _tuple_ends(design, element, width)
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
    if is_pin_tuple(element):
        return pin_tuple(cast("tuple[Port, ...]", element))._series_width()
    if is_mixed_tuple(element):
        return len(cast("tuple[object, ...]", element))
    if isinstance(element, Terminal | tuple):
        return fixed(element)._series_width()
    probe: Any = getattr(element, "_series_width", None)
    return None if probe is None else cast("int | None", probe())


def is_bridge(element: object) -> TypeGuard[SeriesBridge]:
    """True for an element that lands between its neighbours (`SeriesBridge`)."""
    return hasattr(element, "_series_between")
