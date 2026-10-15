"""F4 tests: `marking_key` and `pole_order`, pole order and line side from pin markings.

Every part is invented: a four-pin switch with poles 9/10 and 13/14, and a changed order of links.
Can-fail probe: `marking_key` as a plain text sort fails the 9-before-10 and 1/2-before-13/14 tests.
"""

import itertools
from dataclasses import replace

from fransys_model.kernel import Id
from fransys_model.vocab.enums import FunctionKind, LinkKind, PoleSide, PortRole
from fransys_model.vocab.markings import function_poles, pole_order, unlinked_poles
from fransys_model.vocab.templates import InternalLink, PortTemplate

_FUNCTION = Id(kind="function_template", value="1" * 32)
_COUNTER = itertools.count(1)


def _port(
    marking: str | None, side: PoleSide | None = None, name: str | None = None
) -> PortTemplate:
    """A port template named `name` (default: its marking) with a `pole_side` fact."""
    label = name or marking or "x"
    return PortTemplate(
        id=Id(kind="port_template", value=f"{next(_COUNTER):032d}"),
        key=("t", "fn", "port", label),
        function=_FUNCTION,
        name=label,
        role=PortRole.GENERIC,
        marking=marking,
        pole_side=side,
    )


def _link(a: PortTemplate, b: PortTemplate) -> InternalLink:
    return InternalLink(
        id=Id(kind="internal_link", value=f"{next(_COUNTER):032d}"),
        key=("t", "fn", "link", a.name, b.name),
        a=a.id,
        b=b.id,
        kind=LinkKind.SWITCHED,
    )


def _order(*pairs: tuple[PortTemplate, PortTemplate]):
    ports = {p.id: p for pair in pairs for p in pair}
    return pole_order([_link(a, b) for a, b in pairs], ports)


def _names(poles) -> list[tuple[str, ...]]:
    return [tuple(p.name for p in pole.ends) for pole in poles]


def _fn(kind: FunctionKind, *pairs: tuple[PortTemplate, PortTemplate], link: LinkKind):
    ports = {p.id: p for pair in pairs for p in pair}
    links = [replace(_link(a, b), kind=link) for a, b in pairs]
    return function_poles(kind, links, ports)


def test_unlinked_pins_pair_in_port_order_key_order() -> None:
    """Pins given 10, 2, 9, 1 pair 1/2 and 9/10: marking order, pairs of two."""
    poles = unlinked_poles([_port("10"), _port("2"), _port("9"), _port("1")])
    assert _names(poles) == [("1", "2"), ("9", "10")]


def test_an_odd_pin_is_a_one_pin_pole_last() -> None:
    """Pins 3, 1, 2 give (1, 2) then (3, 3): the odd pin is kept, not dropped."""
    poles = unlinked_poles([_port("3"), _port("1"), _port("2")])
    assert _names(poles) == [("1", "2"), ("3", "3")]
    assert poles[-1].line is None
