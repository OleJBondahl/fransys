"""F4 tests: `natural_key` and `ordered`, pole order and line side from pin markings.

Every part is invented: a four-pin switch with poles 9/10 and 13/14, and a changed order of links.
Can-fail probe: `natural_key` as a plain text sort fails the 9-before-10 and 1/2-before-13/14 tests.
"""

import itertools
from dataclasses import replace

from fransys_model.derive.facts.part_pins import ordered, pair_of, poles_by_links
from fransys_model.elecdef import LinkKind, Side
from fransys_model.kernel import Id
from fransys_model.vocab.enums import PortBoundary
from fransys_model.vocab.templates import InternalLink, PortTemplate

_FUNCTION = Id(kind="function_template", value="1" * 32)
_COUNTER = itertools.count(1)


def _port(marking: str | None, side: Side | None = None, name: str | None = None) -> PortTemplate:
    """A port template named `name` (default: its marking) with a `side` fact."""
    label = name or marking or "x"
    return PortTemplate(
        id=Id(kind="port_template", value=f"{next(_COUNTER):032d}"),
        key=("t", "fn", "port", label),
        function=_FUNCTION,
        name=label,
        boundary=PortBoundary.GENERIC,
        marking=marking,
        side=side,
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
    return ordered(pair_of(ports[a.id], ports[b.id]) for a, b in pairs)


def _names(poles) -> list[tuple[str, ...]]:
    return [tuple(p.name for p in pole.ends) for pole in poles]


def test_a_conductive_link_is_a_pole_only_from_a_line_pin_to_a_load_pin() -> None:
    """`poles_by_links` (elecdef `poles`): a line-to-load conductive link is a pole; one with no sides is not."""
    line, load, bare_a, bare_b = _port("1", Side.A), _port("2", Side.B), _port("3"), _port("4")
    ports = {p.id: p for p in (line, load, bare_a, bare_b)}
    conductive = [replace(_link(a, b), kind=LinkKind.CONDUCTIVE) for a, b in ((line, load), (bare_a, bare_b))]
    assert [(a.name, b.name) for a, b in (p.ends for p in poles_by_links(conductive, ports))] == [("1", "2")]
    assert poles_by_links([replace(_link(bare_a, bare_b), kind=LinkKind.PROTECTIVE)], ports)


def test_a_changeover_takes_its_line_from_its_one_line_side_and_two_line_sides_leave_it_to_each_link() -> None:
    """One side-A common is every pair's line; with two side-A pins elecdef names none, so each link's own side decides (11-12 has none)."""
    common, nc, no = _port("11", Side.A), _port("12", Side.B), _port("14", Side.B)
    ports = {p.id: p for p in (common, nc, no)}
    links = [replace(_link(common, nc)), replace(_link(common, no))]
    assert [(p.line and p.line.name, tuple(e.name for e in p.ends)) for p in poles_by_links(links, ports)] == [
        ("11", ("11", "12")),
        ("11", ("11", "14")),
    ]
    both = {p.id: p for p in (_port("11", Side.A), _port("12", Side.A), _port("14"))}
    first, second, third = both.values()
    found = poles_by_links([_link(first, second), _link(first, third)], both)
    assert [(p.line and p.line.name, tuple(e.name for e in p.ends)) for p in found] == [(None, ("11", "12")), ("11", ("11", "14"))]
