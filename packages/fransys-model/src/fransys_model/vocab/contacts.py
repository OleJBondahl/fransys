"""Changeover throws: which ports of a `CONTACT_CO` function are its common, break and make.

Lives in `vocab`, not `derive`, because `vocab.closure` reads it (`link_state` labels the rail
closure's edges, `rail_pairs`) and a layer imports only the layers to its right; `derive.contacts`
re-exports it (CONTACT-STATES CS2, CS4, decision 0019).
A throw is a part fact, the `PortTemplate.role` `COMMON`/`BREAK`/`MAKE`, never a pin name.
"""

from typing import TYPE_CHECKING, Literal

from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, digest_cached, value

from .core import Function, Port
from .enums import FunctionKind, LinkKind, LinkRest, PortRole
from .tables import functions, internal_links, port_templates, ports
lazy from .templates import InternalLink

if TYPE_CHECKING:
    from .templates import PortTemplate


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


def _pole(a_role: PortRole, b_role: PortRole) -> tuple[bool, PortRole] | None:
    """What a link between ends of roles `a_role` and `b_role` joins, if it joins a pole.

    The one home of "a link joins a common to a throw". Returns `(common_is_a, throw)`, the
    throw `BREAK` or `MAKE`, if one end is `COMMON` and the other a throw, either way; else `None`.
    """
    throws = (PortRole.BREAK, PortRole.MAKE)
    if a_role is PortRole.COMMON and b_role in throws:
        return True, b_role
    if b_role is PortRole.COMMON and a_role in throws:
        return False, a_role
    return None


def _changeover_ports(model: Model) -> dict[Id[PortTemplate], list[Port]]:
    """The ports with a template that belong to a `CONTACT_CO` function, by template."""
    known = functions(model)
    by_template: dict[Id[PortTemplate], list[Port]] = {}
    for port in ports(model).values():
        if port.template is not None and known[port.function].kind is FunctionKind.CONTACT_CO:
            by_template.setdefault(port.template, []).append(port)
    return by_template


def _poles(
    reached: dict[Id[Port], dict[PortRole, set[Id[Port]]]], model: Model
) -> dict[Id[Function], tuple[Throws, ...]]:
    """Each function's `Throws`, one per common in `reached`, sorted by `common`."""
    poles: dict[Id[Function], list[Throws]] = {}
    for common, by_role in reached.items():
        poles.setdefault(ports(model)[common].function, []).append(
            Throws(
                common=common,
                breaks=tuple(sorted(by_role.get(PortRole.BREAK, ()))),
                makes=tuple(sorted(by_role.get(PortRole.MAKE, ()))),
            )
        )
    return {
        function: tuple(sorted(found, key=lambda t: t.common)) for function, found in poles.items()
    }


@digest_cached(DIGEST_CACHE_SIZE)
def _throws(model: Model) -> frozendict[Id[Function], tuple[Throws, ...]]:
    """Every changeover function's poles, for the one digest; a function with none is absent."""
    templates = port_templates(model)
    by_template = _changeover_ports(model)
    by_function_template: dict[tuple[Id[Function], Id[PortTemplate]], list[Port]] = {}
    for template, members in by_template.items():
        for port in members:
            by_function_template.setdefault((port.function, template), []).append(port)
    reached: dict[Id[Port], dict[PortRole, set[Id[Port]]]] = {}
    for link in internal_links(model).values():
        if link.kind is not LinkKind.SWITCHED:
            continue
        pole = _pole(templates[link.a].role, templates[link.b].role)
        if pole is None:
            continue
        common_is_a, throw = pole
        common, thrown = (link.a, link.b) if common_is_a else (link.b, link.a)
        for port in by_template.get(common, ()):
            others = by_function_template.get((port.function, thrown), ())
            if others:
                reached.setdefault(port.id, {}).setdefault(throw, set()).update(
                    other.id for other in others
                )
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
_REST_STATE: dict[LinkRest, LinkState] = {LinkRest.OPEN: "operated", LinkRest.CLOSED: "rest"}


def _kind_state(model: Model, kind: FunctionKind, link: InternalLink) -> LinkState:
    """The state a function kind implies for its switched `link`: NO, NC, or CO by its roles."""
    if kind is FunctionKind.CONTACT_NO:
        return "operated"
    if kind is FunctionKind.CONTACT_NC:
        return "rest"
    templates = port_templates(model)
    a, b = templates.get(link.a), templates.get(link.b)
    if kind is not FunctionKind.CONTACT_CO or a is None or b is None:
        return "both"
    pole = _pole(a.role, b.role)
    if pole is None:
        return "both"
    return "rest" if pole[1] is PortRole.BREAK else "operated"


def link_state(model: Model, function: Id[Function], link: Id[InternalLink]) -> LinkState:
    """The state in which the internal link `link` of the contact `function` is closed.

    A switched link's declared `rest` decides first (`CLOSED` is `"rest"`, `OPEN` `"operated"`).
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
    found = functions(model).get(function)
    joined = internal_links(model).get(link)
    if found is None or joined is None or joined.kind is not LinkKind.SWITCHED:
        return "both"
    if joined.rest is not None:
        return _REST_STATE[joined.rest]
    return _kind_state(model, found.kind, joined)
