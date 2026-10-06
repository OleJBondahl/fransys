"""F4 tests: `marking_key` and `pole_order`, pole order and line side from pin markings.

Every part is invented: a four-pin switch with poles 9/10 and 13/14, and a changed order of links.
Can-fail probe: `marking_key` as a plain text sort fails the 9-before-10 and 1/2-before-13/14 tests.
"""

import itertools
from dataclasses import replace

import pytest

from fransys_model.kernel import Id
from fransys_model.vocab.enums import FunctionKind, LinkKind, PoleSide, PortRole
from fransys_model.vocab.markings import function_poles, marking_key, pole_order, unlinked_poles
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


@pytest.mark.parametrize(
    ("early", "late"),
    [("9", "10"), ("1/2", "13/14"), ("2", "13"), ("13", "A1"), ("A1", "A2"), ("A2", "A10")],
)
def test_marking_key_is_natural_number_order(early: str, late: str) -> None:
    """Numbers go by value, text goes after numbers."""
    assert marking_key(early) < marking_key(late)


def test_pole_9_10_comes_before_pole_13_14() -> None:
    """Links given 13/14 first still come out 9/10 first."""
    poles = _order((_port("13"), _port("14")), (_port("9"), _port("10")))
    assert _names(poles) == [("9", "10"), ("13", "14")]


def test_pole_1_2_comes_before_pole_13_14() -> None:
    """A text sort would put `13` before `2`."""
    poles = _order((_port("13"), _port("14")), (_port("1"), _port("2")))
    assert _names(poles) == [("1", "2"), ("13", "14")]


def test_line_side_is_the_port_whose_pole_side_is_line() -> None:
    """The line end comes first and is named, whatever the markings say."""
    line, load = _port("2", PoleSide.LINE), _port("1", PoleSide.LOAD)
    (pole,) = _order((load, line))
    assert pole.line == line
    assert pole.ends == (line, load)


def test_one_line_side_fact_is_enough() -> None:
    """A pole whose other end states nothing still has its line side."""
    line, other = _port("4", PoleSide.LINE), _port("3")
    (pole,) = _order((other, line))
    assert pole.line == line


def test_no_side_fact_gives_no_line_port_and_marking_order() -> None:
    """Without a fact, `line` is `None` and the ends keep natural marking order."""
    (pole,) = _order((_port("10"), _port("9")))
    assert pole.line is None
    assert _names((pole,)) == [("9", "10")]


def test_unprinted_marking_sorts_by_port_name() -> None:
    """`marking = None` prints the port's name, so it orders by it."""
    poles = _order(
        (_port(None, name="B2"), _port(None, name="B1")),
        (_port(None, name="A2"), _port(None, name="A1")),
    )
    assert _names(poles) == [("A1", "A2"), ("B1", "B2")]


def _fn(kind: FunctionKind, *pairs: tuple[PortTemplate, PortTemplate], link: LinkKind):
    ports = {p.id: p for pair in pairs for p in pair}
    links = [replace(_link(a, b), kind=link) for a, b in pairs]
    return function_poles(kind, links, ports)


def test_a_contactor_gives_its_switched_poles_in_order() -> None:
    line = PoleSide.LINE
    poles = _fn(
        FunctionKind.CONTACT_NO,
        (_port("14", None), _port("13", line)),
        (_port("2", None), _port("1", line)),
        link=LinkKind.SWITCHED,
    )
    assert _names(poles) == [("1", "2"), ("13", "14")]


def test_an_mcb_gives_its_protective_poles() -> None:
    poles = _fn(
        FunctionKind.PROTECTION,
        (_port("2"), _port("1")),
        link=LinkKind.PROTECTIVE,
    )
    assert _names(poles) == [("1", "2")]


def test_an_overload_main_path_is_a_pole() -> None:
    """A protection function's conductive link is a pole (F1); dropping that kind fails this."""
    poles = _fn(FunctionKind.PROTECTION, (_port("1"), _port("2")), link=LinkKind.CONDUCTIVE)
    assert _names(poles) == [("1", "2")]


def test_a_terminals_conductive_link_is_no_pole() -> None:
    assert _fn(FunctionKind.TERMINAL, (_port("1"), _port("2")), link=LinkKind.CONDUCTIVE) == ()


def test_unlinked_pins_pair_in_port_order_key_order() -> None:
    """Pins given 10, 2, 9, 1 pair 1/2 and 9/10: marking order, pairs of two."""
    poles = unlinked_poles([_port("10"), _port("2"), _port("9"), _port("1")])
    assert _names(poles) == [("1", "2"), ("9", "10")]
