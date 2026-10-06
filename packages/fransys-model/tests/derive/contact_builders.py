"""Shared builders for the CONTACT-STATES CS2 tests: an invented changeover relay part.

`test_changeover_throws` and `test_link_state` both build one part whose contact functions have
ports with a `PortTemplate.role`, then instantiate it on one or more items. Names keep their
leading underscore, as the sibling test modules that share builders do.
"""

from typing import TYPE_CHECKING

from derive_helpers import add_all
from examples import bundle_records

from fransys_model.kernel import Draft, Id, Model, Origin, freeze, make_id
from fransys_model.vocab.core import Function, Port
from fransys_model.vocab.enums import FunctionKind, LinkKind, LinkRest, PartCategory, PortRole
from fransys_model.vocab.instantiate import PartBundle, instantiate
from fransys_model.vocab.templates import FunctionTemplate, InternalLink, Part, PortTemplate

if TYPE_CHECKING:
    from collections.abc import Sequence

_PART_KEY = ("cs2", "relay")
_ITEM_KEY = ("cs2", "k1")
_ROLES = (PortRole.COMMON, PortRole.BREAK, PortRole.MAKE)
_NUMBERED = ("11", "12", "14")


def _bundle(  # noqa: PLR0913 -- a test builder; every option is a keyword with a default
    poles: Sequence[tuple[str, str, str]] = (_NUMBERED,),
    *,
    roles: tuple[PortRole, PortRole, PortRole] = _ROLES,
    kind: FunctionKind = FunctionKind.CONTACT_CO,
    reverse: bool = False,
    link_kind: LinkKind = LinkKind.SWITCHED,
    rest: LinkRest | None = None,
) -> PartBundle:
    """One part with a contact function per pole; each pole's ports are (first, second, third).

    `roles` gives the three ports' roles in that order; the links join the first port to the
    second and to the third, written `a`=first unless `reverse`.
    """
    part = Part(
        id=make_id(Part, _PART_KEY),
        key=_PART_KEY,
        mpn="CS2-RELAY-1",
        manufacturer="Example Co",
        description="Invented changeover relay for tests",
        category=PartCategory.ELECTROMECHANICAL,
        class_code="K",
    )
    functions: list[FunctionTemplate] = []
    ports: list[PortTemplate] = []
    links: list[InternalLink] = []
    for number, names in enumerate(poles, start=1):
        function_key = (*_PART_KEY, "fn", f"co_{number}")
        function = FunctionTemplate(
            id=make_id(FunctionTemplate, function_key),
            key=function_key,
            part=part.id,
            name=f"co_{number}",
            kind=kind,
        )
        functions.append(function)
        made = [
            PortTemplate(
                id=make_id(PortTemplate, (*function_key, "port", name)),
                key=(*function_key, "port", name),
                function=function.id,
                name=name,
                role=role,
            )
            for name, role in zip(names, roles, strict=True)
        ]
        ports.extend(made)
        for other in made[1:]:
            ends = (made[0].id, other.id)
            link_key = (*function_key, "link", other.name)
            links.append(
                InternalLink(
                    id=make_id(InternalLink, link_key),
                    key=link_key,
                    a=ends[1] if reverse else ends[0],
                    b=ends[0] if reverse else ends[1],
                    kind=link_kind,
                    rest=rest,
                )
            )
    return PartBundle(
        part=part,
        function_templates=tuple(functions),
        port_templates=tuple(ports),
        internal_links=tuple(links),
    )


def _model(bundle: PartBundle, origin: Origin, *item_keys: tuple[str, ...]) -> Model:
    """A frozen model holding `bundle` and one item per key in `item_keys` (default one)."""
    draft = Draft()
    add_all(draft, *bundle_records(bundle), origin=origin)
    for key in item_keys or (_ITEM_KEY,):
        add_all(draft, *instantiate(bundle, key), origin=origin)
    return freeze(draft)


def _function(number: int, item_key: tuple[str, ...] = _ITEM_KEY) -> Id[Function]:
    return make_id(Function, (*item_key, "fn", f"co_{number}"))


def _port(number: int, name: str, item_key: tuple[str, ...] = _ITEM_KEY) -> Id[Port]:
    return make_id(Port, (*item_key, "fn", f"co_{number}", "port", name))


def _link(number: int, other: str) -> Id[InternalLink]:
    """The template link of function `co_<number>` that joins its first port to port `other`."""
    return make_id(InternalLink, (*_PART_KEY, "fn", f"co_{number}", "link", other))
