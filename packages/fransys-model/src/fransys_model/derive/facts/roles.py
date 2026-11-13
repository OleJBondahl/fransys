"""The role readers: the one home of `Function.kind`, `Port.boundary` and the other kind fields.

Each reader is the table row of `vocab/roles.py`, refined by the facets the one site may read
(EL-2a, model-0288). A drawing decision reads a role, never a kind.
"""

from dataclasses import replace
from typing import Any

from fransys_model.derive.accessory_blocks import operating_item
from fransys_model.derive.facts.figures import breaking
from fransys_model.derive.facts.net_facts import net_class_of
from fransys_model.derive.facts.part_pins import poles_by_links
from fransys_model.derive.facts.rating_index import function_block
from fransys_model.elecdef import LinkKind, PinRole
from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, digest_cached
from fransys_model.vocab.enums import FunctionKind, PortBoundary
from fransys_model.vocab.facets.plc import PlcChannelFacet
from fransys_model.vocab.roles import (
    CONDUCTOR_ROLES,
    LINK_ROLES,
    NET_CLASS_ROLES,
    function_role_of,
)
from fransys_model.vocab.tables import (
    HasTables,
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
lazy from fransys_model.vocab.templates import (
    FunctionTemplate,
    InternalLink,
    Part,
)


def _refined(model: Model, function: Function, channels: frozenset[Id[Any] | None]) -> FunctionRole:
    """The row of `function.kind`, refined by its template, its rating and its holder."""
    role = function_role_of(function.kind)
    template = None if function.template is None else function_templates(model)[function.template]
    if template is not None and template.energy is not None:
        role = replace(role, energy=template.energy)
    if function.template in channels:
        role = replace(role, channel=True)
    if breaking(function_block(model, function.id)):
        role = replace(role, protects=True)
    if operating_item(model, function.id) == function.item:
        role = replace(role, operator=True)
    return role


@digest_cached(DIGEST_CACHE_SIZE)
def plc_channel_facets(model: Model) -> frozendict[Id[FunctionTemplate] | None, PlcChannelFacet]:
    """The one reading of "is a PLC channel": each channel template's facet, keyed by it."""
    return frozendict({f.subject: f for f in facets_of(model, PlcChannelFacet).values()})


def function_channel(model: Model, function: Id[Function]) -> PlcChannelFacet | None:
    """The `plc_channel` facet of `function`'s template, or `None` when it is not a channel."""
    template = functions(model)[function].template
    return None if template is None else plc_channel_facets(model).get(template)


@digest_cached(DIGEST_CACHE_SIZE)
def _function_roles(model: Model) -> frozendict[Id[Function], FunctionRole]:
    """Every function's refined role, built once per model digest."""
    channels = frozenset(plc_channel_facets(model))
    return frozendict({f.id: _refined(model, f, channels) for f in functions(model).values()})


def function_role(model: Model, function: Id[Function]) -> FunctionRole:
    """The role of `function`: its kind's row refined by its template, rating and holder.

    A template's energy, a channel facet, a breaking rating and an operating holder apply.

    Example: `function_role(model, fn).contact` is true for a normally open, a normally closed or
    a changeover contact and for a switch, and false for a coil.
    """
    return _function_roles(model)[function]


def link_role(model: HasTables, link: Id[InternalLink]) -> LinkRole:
    """The role of an internal link: its kind's row, with the pole and rest the function adds.

    A conductive link between a line and a load pin is a pole; a switched link rests as declared,
    else as its function's kind implies.
    """
    record = internal_links(model)[link]
    role = LINK_ROLES[record.kind]
    ends = {end: port_templates(model)[end] for end in (record.a, record.b)}
    kind = function_templates(model)[ends[record.a].function].kind
    role = replace(role, pole=bool(poles_by_links([record], ends)))
    if record.kind is not LinkKind.SWITCHED:
        return role
    declared = record.closed_at_rest
    return replace(role, closed_at_rest=function_role_of(kind).closed_at_rest if declared is None else declared)


def link_rest(model: Model, link: Id[InternalLink]) -> bool | None:
    """The state at rest of an internal link: as declared, else its function's kind implies."""
    return link_role(model, link).closed_at_rest


def conductor_role(model: Model, conductor: Id[Conductor]) -> ConductorRole:
    """The role of a conductor: its kind's row."""
    return CONDUCTOR_ROLES[conductors(model)[conductor].kind]


def net_class_role(model: Model, net: Id[Net]) -> NetClassRole:
    """The role of a declared net: its class's row."""
    return NET_CLASS_ROLES[net_class_of(model, net)]


def port_boundary(model: Model, port: Id[Port]) -> PortBoundary:
    """The `PortBoundary` of `port`: the one reader of `Port.boundary`."""
    return ports(model)[port].boundary


def is_internal_port(model: Model, port: Id[Port]) -> bool:
    """Whether `port` is on the internal (panel wiring) side of its unit boundary."""
    return port_boundary(model, port) is PortBoundary.INTERNAL


def port_pin_role(model: Model, port: Id[Port]) -> PinRole | None:
    """The pin role of `port`, `None` if the part states none: the one reader of `Port.pin_role`."""
    return ports(model)[port].pin_role


def is_pe_port(model: Model, port: Id[Port]) -> bool:
    """Whether `port` has pin role PE: the one compare of `PinRole.PE`."""
    return port_pin_role(model, port) is PinRole.PE


def changeover_functions(model: Model) -> set[tuple[Id[Part], str]]:
    """The (part, name) of every changeover function template (its kind is the one fact)."""
    return {(template.part, template.name) for template in function_templates(model).values() if template.kind is FunctionKind.CONTACT_CO}
