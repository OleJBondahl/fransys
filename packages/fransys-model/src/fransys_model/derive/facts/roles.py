"""The role readers: the one home of `Function.kind`, `Port.role` and the other kind fields.

Each reader is the table row of `vocab/roles.py`, refined by the facets the one site may read
(EL-2a, model-0288). A drawing decision reads a role, never a kind.
"""

from dataclasses import replace
from typing import Any

from fransys_model.derive.accessory_blocks import operating_item
from fransys_model.derive.facts.function_ratings import function_rating
from fransys_model.derive.facts.net_facts import net_class_of
from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, digest_cached
from fransys_model.vocab.enums import FunctionKind, LinkKind, LinkRest, PortRole
from fransys_model.vocab.facets.plc import PlcChannelFacet
from fransys_model.vocab.roles import (
    CONDUCTOR_ROLES,
    FUNCTION_ROLES,
    LINK_ROLES,
    NET_CLASS_ROLES,
)
from fransys_model.vocab.tables import (
    conductors,
    facets_of,
    function_templates,
    functions,
    internal_links,
    port_templates,
    ports,
)
lazy from fransys_model.vocab.connectivity import Conductor, Net
lazy from fransys_model.vocab.core import Function, Port
lazy from fransys_model.vocab.roles_types import (
    ConductorRole,
    FunctionRole,
    LinkRole,
    NetClassRole,
)
lazy from fransys_model.vocab.templates import InternalLink, Part


def _refined(model: Model, function: Function, channels: frozenset[Id[Any]]) -> FunctionRole:
    """The row of `function.kind`, refined by its template, its rating and its holder."""
    role = FUNCTION_ROLES[function.kind]
    template = None if function.template is None else function_templates(model)[function.template]
    if template is not None and template.energy is not None:
        role = replace(role, energy=template.energy)
    if function.template in channels:
        role = replace(role, channel=True)
    rating = function_rating(model, function.id)
    if rating is not None and (rating.breaking_ac or rating.breaking_dc):
        role = replace(role, protects=True)
    if operating_item(model, function.id) == function.item:
        role = replace(role, operator=True)
    return role


@digest_cached(DIGEST_CACHE_SIZE)
def _function_roles(model: Model) -> frozendict[Id[Function], FunctionRole]:
    """Every function's refined role, built once per model digest."""
    channels = frozenset(f.subject for f in facets_of(model, PlcChannelFacet).values())
    return frozendict({f.id: _refined(model, f, channels) for f in functions(model).values()})


def function_role(model: Model, function: Id[Function]) -> FunctionRole:
    """The role of `function`: its kind's row refined by its template, rating and holder.

    A template's energy, a channel facet, a breaking rating and an operating holder apply.

    Example: `function_role(model, fn).contact` is true for a normally open, a normally closed or
    a changeover contact and for a switch, and false for a coil.
    """
    return _function_roles(model)[function]


def link_role(model: Model, link: Id[InternalLink]) -> LinkRole:
    """The role of an internal link: its kind's row, with the pole and rest the function adds.

    A protection's conductive link is a pole; a switched link rests as declared, else as its
    function's kind implies.
    """
    record = internal_links(model)[link]
    role = LINK_ROLES[record.kind]
    kind = function_templates(model)[port_templates(model)[record.a].function].kind
    if kind is FunctionKind.PROTECTION and record.kind is LinkKind.CONDUCTIVE:
        role = replace(role, pole=True)
    if record.kind is not LinkKind.SWITCHED:
        return role
    return replace(role, rest=record.rest or FUNCTION_ROLES[kind].rest)


def link_rest(model: Model, link: Id[InternalLink]) -> LinkRest | None:
    """The state at rest of an internal link: as declared, else its function's kind implies."""
    return link_role(model, link).rest


def conductor_role(model: Model, conductor: Id[Conductor]) -> ConductorRole:
    """The role of a conductor: its kind's row."""
    return CONDUCTOR_ROLES[conductors(model)[conductor].kind]


def net_class_role(model: Model, net: Id[Net]) -> NetClassRole:
    """The role of a declared net: its class's row."""
    return NET_CLASS_ROLES[net_class_of(model, net)]


def port_role(model: Model, port: Id[Port]) -> PortRole:
    """The `PortRole` of `port`: the one reader of `Port.role`."""
    return ports(model)[port].role


def changeover_functions(model: Model) -> set[tuple[Id[Part], str]]:
    """The (part, name) of every changeover function template (its kind is the one fact)."""
    return {
        (template.part, template.name)
        for template in function_templates(model).values()
        if template.kind is FunctionKind.CONTACT_CO
    }
