"""F4 tests: `natural_key` and `pole_order`, pole order and line side from pin markings.

Every part is invented: a four-pin switch with poles 9/10 and 13/14, and a changed order of links.
Can-fail probe: `natural_key` as a plain text sort fails the 9-before-10 and 1/2-before-13/14 tests.
"""

import itertools

from fransys_model.elecdef import LinkKind, Side
from fransys_model.kernel import Id
from fransys_model.vocab.enums import PortBoundary
from fransys_model.vocab.markings import (
    is_pole_by_role,
    pole_order,
)
from fransys_model.vocab.roles_types import FunctionRole
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
    return pole_order([_link(a, b) for a, b in pairs], ports)


def _names(poles) -> list[tuple[str, ...]]:
    return [tuple(p.name for p in pole.ends) for pole in poles]


def test_a_conductive_link_is_a_pole_by_the_protects_flag_not_by_the_kind() -> None:
    """`is_pole_by_role`: a role that protects makes its conductive link a pole; no other does."""
    protects = FunctionRole(protects=True)
    assert is_pole_by_role(protects, LinkKind.CONDUCTIVE)
    assert not is_pole_by_role(FunctionRole(), LinkKind.CONDUCTIVE)
    assert is_pole_by_role(FunctionRole(), LinkKind.SWITCHED)
    assert is_pole_by_role(FunctionRole(), LinkKind.PROTECTIVE)
