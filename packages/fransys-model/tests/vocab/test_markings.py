"""F4 tests: `natural_key` and `pole_order`, pole order and line side from pin markings.

Every part is invented: a four-pin switch with poles 9/10 and 13/14, and a changed order of links.
Can-fail probe: `natural_key` as a plain text sort fails the 9-before-10 and 1/2-before-13/14 tests.
"""

import itertools
from dataclasses import replace

from fransys_model.kernel import Id
from fransys_model.vocab.enums import FunctionKind, LinkKind, PoleSide, PortRole
from fransys_model.vocab.markings import (
    function_poles,
    is_pole_by_role,
    pole_order,
    poles_by_role,
)
from fransys_model.vocab.roles import function_role_of
from fransys_model.vocab.roles_types import FunctionRole
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


def test_a_conductive_link_is_a_pole_by_the_protects_flag_not_by_the_kind() -> None:
    """`is_pole_by_role`: a role that protects makes its conductive link a pole; no other does."""
    protects = FunctionRole(protects=True)
    assert is_pole_by_role(protects, LinkKind.CONDUCTIVE)
    assert not is_pole_by_role(FunctionRole(), LinkKind.CONDUCTIVE)
    assert is_pole_by_role(FunctionRole(), LinkKind.SWITCHED)
    assert is_pole_by_role(FunctionRole(), LinkKind.PROTECTIVE)


def test_the_kind_wrappers_equal_the_role_form_for_every_kind() -> None:
    """`function_poles` is `poles_by_role` read at the kind's row."""
    a, b = _port("1"), _port("2")
    ports = {a.id: a, b.id: b}
    for kind in FunctionKind:
        role = function_role_of(kind)
        for link in LinkKind:
            links = [replace(_link(a, b), kind=link)]
            assert function_poles(kind, links, ports) == poles_by_role(role, links, ports)
