"""Changeover throws: which ports of a `CONTACT_CO` function are its common, break and make.

`derive.contacts` re-exports it (CONTACT-STATES CS2, CS4, decision 0019); `link_state` labels the
rail closure's edges. A throw is a part fact, the `PortTemplate.pin_role` `COMMON`/`BREAK`/`MAKE`,
never a pin name.
"""

from typing import Literal

from fransys_model.derive.facts.part_pins import template_throws
from fransys_model.derive.facts.roles import function_role, link_rest, link_role
from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, digest_cached, value
from fransys_model.vocab.tables import functions, internal_links, port_templates, ports
lazy from fransys_model.vocab.core import Function, Port
lazy from fransys_model.vocab.templates import InternalLink, PortTemplate


@value
class Throws:
    """One pole of a changeover: its common port and the throws a switched link joins to it.

    `breaks` are the ports the common closes to at rest, `makes` those it closes to when
    operated; both sorted by id, so two computations over the same model compare equal.
    Example: the invented relay's `co_1` with `11` common, `12` break and `14` make gives
    `Throws(common=<11>, breaks=(<12>,), makes=(<14>,))`.

    Attributes:
        common: The pole's common port.
        breaks: The ports the common closes to at rest, sorted by id.
        makes: The ports the common closes to when operated, sorted by id.
    """

    common: Id[Port]
    breaks: tuple[Id[Port], ...]
    makes: tuple[Id[Port], ...]


def _changeover_ports(model: Model) -> dict[Id[PortTemplate], list[Port]]:
    """The ports with a template that belong to a `CONTACT_CO` function, by template."""
    by_template: dict[Id[PortTemplate], list[Port]] = {}
    for port in ports(model).values():
        if port.template is not None and function_role(model, port.function).changeover:
            by_template.setdefault(port.template, []).append(port)
    return by_template


def _poles(reached: dict[Id[Port], dict[bool, set[Id[Port]]]], model: Model) -> dict[Id[Function], tuple[Throws, ...]]:
    """Each function's `Throws`, one per common in `reached`, sorted by `common`."""
    poles: dict[Id[Function], list[Throws]] = {}
    for common, by_role in reached.items():
        poles.setdefault(ports(model)[common].function, []).append(
            Throws(
                common=common,
                breaks=tuple(sorted(by_role.get(True, ()))),
                makes=tuple(sorted(by_role.get(False, ()))),
            )
        )
    return {function: tuple(sorted(found, key=lambda t: t.common)) for function, found in poles.items()}


@digest_cached(DIGEST_CACHE_SIZE)
def _throws(model: Model) -> frozendict[Id[Function], tuple[Throws, ...]]:
    """Every changeover function's poles, for the one digest; a function with none is absent."""
    templates = port_templates(model)
    by_template = _changeover_ports(model)
    by_function_template: dict[tuple[Id[Function], Id[PortTemplate]], list[Port]] = {}
    for template, members in by_template.items():
        for port in members:
            by_function_template.setdefault((port.function, template), []).append(port)
    reached: dict[Id[Port], dict[bool, set[Id[Port]]]] = {}
    for link in internal_links(model).values():
        for common, thrown, closed_at_rest in template_throws(templates, (link,)):
            for port in by_template.get(common, ()):
                others = by_function_template.get((port.function, thrown), ())
                if others:
                    reached.setdefault(port.id, {}).setdefault(closed_at_rest, set()).update(other.id for other in others)
    return frozendict(_poles(reached, model))


def changeover_throws(model: Model, function: Id[Function]) -> tuple[Throws, ...]:
    """The poles of the `CONTACT_CO` function `function`, one `Throws` per common port.

    A common port gets a `Throws` when a `switched` internal link joins it to a `BREAK` or `MAKE`
    port of the same function. Roles come from the part's `PortTemplate`s, never a pin name.
    Sorted by `common`; it never raises. Cached on `model.digest`.

    Args:
        model: The model to read.
        function: The `CONTACT_CO` function whose poles are found.

    Returns:
        One `Throws` per common port, sorted by `common`; empty for a function that is not a
        changeover, is not in `model`, or whose ports carry no `COMMON`/`BREAK`/`MAKE` roles.
    """
    return _throws(model).get(function, ())


# A link's closed state: "rest" (closed at rest: a normally closed contact, a changeover's break,
# a switched link declared `rest` closed), "operated" (closed when operated), or "both" (always
# closed, or not governed by a contact: a `CONDUCTIVE` or `PROTECTIVE` link, or an undeclared
# switched link of a switch or generic function, which parts lint refuses).
LinkState = Literal["rest", "operated", "both"]


def _changeover_state(model: Model, link: InternalLink) -> LinkState:
    """The state of a changeover's switched `link`: the rest of the elecdef throw it makes, else "both"."""
    templates = port_templates(model)
    if link.a not in templates or link.b not in templates:
        return "both"
    found = template_throws(templates, (link,))
    return "both" if not found else "rest" if found[0][2] else "operated"


def link_state(model: Model, function: Id[Function], link: Id[InternalLink]) -> LinkState:
    """The state in which the internal link `link` of the contact `function` is closed.

    A switched link's declared `rest` decides first (closed is `"rest"`, open `"operated"`).
    Otherwise `CONTACT_NO` implies `"operated"`, `CONTACT_NC` `"rest"`, and `CONTACT_CO` the roles
    of the link's ends through `_pole` (common to `BREAK` `"rest"`, to `MAKE` `"operated"`).
    Anything else is `"both"`, an unknown id too; it never raises.

    Args:
        model: The model to read.
        function: The contact function the link belongs to.
        link: The internal link whose closed state is found.

    Returns:
        `"rest"`, `"operated"`, or `"both"`.
    """
    joined = internal_links(model).get(link)
    if function not in functions(model) or joined is None or not link_role(model, link).switched:
        return "both"
    rest = link_rest(model, link)
    if rest is not None:
        return "rest" if rest else "operated"
    return _changeover_state(model, joined) if function_role(model, function).changeover else "both"
