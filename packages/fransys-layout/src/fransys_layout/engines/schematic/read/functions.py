"""How one `FunctionSpec` is read: the machinery `reading.drawn_functions` needs.

Poles and aspect paths are read here; the pole-pairing rule itself is
`stages.resolve.poles_and_pairs`, which gets the values this module reads. The cable/board
exclusion moved to `fransys_model.derive.schematic_functions` (model-0039):
`reading.drawn_functions` filters `functions(model)` through it instead of a private copy of
the walk. Placement resolution moved to `fransys_model.derive.effective_placement`
(model-0040): `_placement_leaf` reads through it instead of a private,
item-only lookup, so a board connector with no placement of its own draws in its nearest
placed ancestor's drawing set.
"""

import dataclasses
from typing import TYPE_CHECKING, Any

from fransys_layout.engines.schematic.defaults import kind_roles
from fransys_layout.stages import FunctionSpec
from fransys_layout.stages.resolve import poles_and_pairs
from fransys_model.derive import (
    actuated_group,
    actuator_each_contact,
    effective_placement,
    lead_switch,
    operated_by,
    operating_item,
)
from fransys_model.derive.designation import reference_designation
from fransys_model.derive.drawing_text import point_text, strip_tag_text
from fransys_model.derive.lookups import connector_facets
from fransys_model.kernel import SchemaError, parent_chain
from fransys_model.vocab import function_poles, marking_key, pole_order
from fransys_model.vocab.enums import Aspect
from fransys_model.vocab.tables import (
    aspect_nodes,
    internal_links,
    items,
    parts,
    port_templates,
    ports,
)

from . import roles
from .rest import function_rest, protection_type
from .text_or_empty import text_or_empty

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from fransys_layout.stages import PortSpec
    from fransys_model.derive.indexes import Indexes
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Pole
    from fransys_model.vocab.aspects import AspectNode
    from fransys_model.vocab.core import Function, Item, Unit


def in_marking_order(specs: Iterable[PortSpec]) -> tuple[PortSpec, ...]:
    """`specs` with `order` set to the rank of each name's `marking_key` (`10` after `2`)."""
    ranked = sorted(specs, key=lambda spec: (marking_key(spec.name), spec.name))
    return tuple(dataclasses.replace(spec, order=i) for i, spec in enumerate(ranked))


def function_spec(
    model: Model,
    indexes: Indexes,
    function: Function,
    group_hints: Mapping[Id[Function], Id[AspectNode]],
) -> FunctionSpec:
    """One `FunctionSpec` read from `function`; `unit` is the item's own `unit`."""
    item = items(model)[function.item]
    category = parts(model)[item.part].category.value if item.part is not None else None
    found = _vocab_poles(model, function)
    poles, pole_pairs = poles_and_pairs((pole.ends[0].name, pole.ends[1].name) for pole in found)
    port_ids = indexes.ports_by_function.get(function.id, ())
    thrown = _throws(model, function, found)
    port_specs = in_marking_order(
        roles.port_spec(model, indexes, port_id, *thrown.get(port_id, (None, 0)))
        for port_id in port_ids
    )
    strip, point = _terminal_texts(model, function)
    group_leaf = _placement_leaf(model, item.id, Aspect.FUNCTION)
    location_leaf = _placement_leaf(model, item.id, Aspect.LOCATION)
    switch_group, actuator = _switch_group(model, function, item.unit)
    return FunctionSpec(
        function=function.id,
        item=item.id,
        part=item.part,
        key=function.key,
        kind=function.kind.value,
        category=category,
        poles=poles,
        pole_pairs=pole_pairs,
        ports=port_specs,
        group_path=_path_root_to_leaf(model, group_leaf),
        location_path=_path_root_to_leaf(model, location_leaf),
        group_hint=group_hints.get(function.id),
        designation=_designation(model, item.id),
        strip_text=strip,
        point_text=point,
        gender=_gender(model, function.template),
        unit=item.unit,
        rack="" if item.parent is None else _designation(model, item.parent),
        rack_position=item.position,
        roles=kind_roles(function.kind.value),
        item_parent=item.parent,
        rest=function_rest(model, function),
        protection_type=protection_type(model, function.template),
        operated_by=_operated_by(model, function),
        switch_group=switch_group,
        actuator=actuator,
    )


def _throws(
    model: Model, function: Function, found: tuple[Pole, ...]
) -> dict[Id[Any], tuple[str, int]]:
    """Each changeover port's throw and pole: its common's place in the vocab pole order."""
    thrown = roles.changeover_throw_of(model, function)
    first: dict[str, int] = {}
    for index, pole in enumerate(found):
        for end in pole.ends:
            first.setdefault(end.name, index)
    names = ports(model)
    commons = sorted({c for _, c in thrown.values()}, key=lambda c: first[names[c].name])
    return {port: (throw, commons.index(common)) for port, (throw, common) in thrown.items()}


def _terminal_texts(model: Model, function: Function) -> tuple[str, str]:
    """A terminal's strip tag and point text, empty before numbering or for any other kind."""
    if function.kind.value != "terminal":
        return "", ""
    try:
        return strip_tag_text(model, function.id), point_text(model, function.id)
    except SchemaError:
        return "", ""


def _gender(model: Model, template: Id[Any] | None) -> str | None:
    """The connector facet's gender of a function template, `None` without one."""
    shape = None if template is None else connector_facets(model).get(template)
    return None if shape is None or shape.gender is None else shape.gender.value


def _designation(model: Model, item: Id[Any]) -> str:
    """The item's reference designation, or "" before the numbering pass."""
    return text_or_empty(reference_designation, model, item)


def _vocab_poles(model: Model, function: Function) -> tuple[Pole, ...]:
    """The poles in the vocab pole order; with no pole link, the linked ports pair."""
    template = function.template
    if template is None:
        return ()
    own = {t.id: t for t in port_templates(model).values() if t.function == template}
    links = [k for k in internal_links(model).values() if k.a in own and k.b in own]
    return function_poles(function.kind, links, own) or pole_order(links, own)


def _placement_leaf(model: Model, item_id: Id[Item], aspect: Aspect) -> AspectNode | None:
    """The leaf node of `item_id`'s own or nearest placed ancestor's placement; smallest id wins."""
    node_id = effective_placement(model, item_id, aspect)
    return None if node_id is None else aspect_nodes(model)[node_id]


def _path_root_to_leaf(model: Model, leaf: AspectNode | None) -> tuple[Id[AspectNode], ...]:
    """The node ids from the root down to `leaf`, empty when `leaf` is `None`."""
    if leaf is None:
        return ()
    nodes = aspect_nodes(model)
    return tuple(reversed(list(parent_chain(lambda node: nodes[node].parent, leaf.id))))


def _operated_by(model: Model, function: Function) -> str | None:
    """`derive.operated_by`'s value as a string, None when no part states one (layout-0220)."""
    found = operated_by(model, function.id)
    return None if found is None else found.value


def _switch_group(
    model: Model, function: Function, unit: Id[Unit] | None
) -> tuple[Id[Item] | None, bool]:
    """layout-0237: a grouped switch's operating item, and whether it is the lead (the actuator).

    layout-0254: with the unit's `actuator_each_contact` profile on (default), no switch is grouped.
    """
    if actuator_each_contact(model, unit):
        return None, True
    if len(actuated_group(model, function.id)) < 2:  # noqa: PLR2004 -- a group of one draws as today (AO6)
        return None, True
    return operating_item(model, function.id), lead_switch(model, function.id) == function.id
