"""The throws and the contact kind of a part's function, over plain templates (EL-5).

CON-01, CON-04, CON-05. A throw is a part fact, the `PortTemplate.role` `COMMON`/`BREAK`/`MAKE`,
never a pin name. The author reads a library, not a model, so every fact takes templates.
"""

lazy from collections.abc import Iterable, Mapping

from fransys_model.derive.facts.contacts import link_throw
from fransys_model.kernel import value
from fransys_model.vocab.enums import FunctionKind, LinkRest, PortRole
from fransys_model.vocab.markings import port_order_key
from fransys_model.vocab.roles import function_role_of
from fransys_model.vocab.throws import THROWS
lazy from fransys_model.kernel import Id
lazy from fransys_model.vocab.templates import InternalLink, PortTemplate


@value
class TemplateThrow:
    """One switched link of a changeover: its `common`, the `throw` it joins and the throw's `role`.

    `closed_at_rest` is the table's answer for `role`: true for a break throw, false for a make.
    Example: the invented relay's `11-12` link gives `(common=11, role=BREAK, throw=12)`.
    """

    common: Id[PortTemplate]
    role: PortRole
    throw: Id[PortTemplate]
    closed_at_rest: bool


def throws_of(
    links: Iterable[InternalLink], templates: Mapping[Id[PortTemplate], PortTemplate]
) -> tuple[TemplateThrow, ...]:
    """Each switched link that joins a common to a throw, in the marking order of its ends.

    The roles come from the templates; the rest state of each throw is the `THROWS` row.
    """
    found = (joined for link in links if (joined := link_throw(link, templates)) is not None)
    triples = sorted(
        found,
        key=lambda t: (port_order_key(templates[t[0]]), port_order_key(templates[t[2]])),
    )
    return tuple(
        TemplateThrow(
            common=common,
            role=role,
            throw=throw,
            closed_at_rest=THROWS[role].closed_at_rest is True,
        )
        for common, role, throw in triples
    )


def contact_kind_of(kind: FunctionKind) -> str | None:
    """`no`, `nc` or `co` for a plain contact function, else `None` (a switch has none)."""
    role = function_role_of(kind)
    if not role.plain_contact:
        return None
    if role.changeover:
        return "co"
    return THROWS[PortRole.BREAK if role.rest is LinkRest.CLOSED else PortRole.MAKE].word


def is_contact_kind(kind: FunctionKind) -> bool:
    """True for a contact function kind, a switch included (CON-01)."""
    return function_role_of(kind).contact


def implied_rest(kind: FunctionKind) -> str | None:
    """`open` or `closed` for a contact kind that implies its rest state, else `None`.

    Example: `contact_no` is `open`; a changeover and a switch imply none.
    """
    role = function_role_of(kind)
    return role.rest.value if role.contact and role.rest is not None else None
