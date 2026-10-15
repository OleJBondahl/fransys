"""A series between two functions with no line side: pins pair in pin order (C6.2, author-0045)."""

from typing import TYPE_CHECKING, cast

from fransys_author.errors import AuthorError
from fransys_author.surface._handles import Fn, fn_label
from fransys_author.surface._pairing import End, Ends, ends_of
from fransys_model.derive import sideless_pins
from fransys_model.vocab import FunctionKind, PortRole

if TYPE_CHECKING:
    from fransys_author.handles import Port

    from .design import Design

type _Pins = tuple[Port, ...]


class _Bare:
    """A function whose pins stand as both its line and its load ends, in pin order.

    Does not pair anything: the series pairs this element's pins with the other end's.
    """

    def __init__(self, ports: _Pins) -> None:
        ends = tuple(End(port, None) for port in ports)
        self._ends = Ends(ends, ends)

    def _series_width(self) -> int:
        return len(self._ends.line)

    def _series_ends(self, design: Design, width: int | None) -> Ends:  # noqa: ARG002 -- the protocol
        return self._ends


def _label(element: object) -> str:
    return fn_label(cast("Fn", element))


def _pins(design: Design, element: object) -> _Pins:
    """The pins of a function with no pole; empty for any other element."""
    if not isinstance(element, Fn) or element._fn.kind is FunctionKind.CONTACT_CO:
        return ()
    if ends_of(design._pairing_facts, element._fn).line:
        return ()
    return tuple(port for port in element._fn.ports if port.role is not PortRole.PE)


def _in_pin_order(
    design: Design, ends: tuple[object, object], pins: tuple[_Pins, _Pins]
) -> tuple[_Pins, _Pins]:
    """Both ends' pins in pin order; raise `derive`'s text when they cannot pair."""
    facts = design._pairing_facts
    by_id = [{facts.port_template(port).id: port for port in end} for end in pins]
    templates = [tuple(facts.port_template(port) for port in end) for end in pins]
    found = sideless_pins(_label(ends[0]), templates[0], _label(ends[1]), templates[1])
    if found.problem:
        raise AuthorError(found.problem)
    return (
        tuple(by_id[0][t.id] for t in found.first),
        tuple(by_id[1][t.id] for t in found.second),
    )


def bare_series(design: Design, elements: tuple[object, ...]) -> tuple[object, ...]:
    """`elements` with both end functions as pin-order elements when both have no pole.

    Any other function with no pole is left as it is, and raises "has no poles" when the series
    reads its ends: in the middle, or at one end against a supply, a rail or a function with poles.
    """
    ends = elements[0], elements[-1]
    pins = _pins(design, ends[0]), _pins(design, ends[1])
    if not all(pins):
        return elements
    first, second = _in_pin_order(design, ends, pins)
    return (_Bare(first), *elements[1:-1], _Bare(second))
