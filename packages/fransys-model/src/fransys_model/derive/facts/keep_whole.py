"""The sets of things that must stay on one page or block: add-on items, pole groups, line units."""

import dataclasses

from fransys_model.derive.facts.children import children_index
from fransys_model.derive.facts.unit_index import unit_index
from fransys_model.derive.facts.units import is_harness
from fransys_model.derive.line_fact import line_conductors
from fransys_model.kernel import DIGEST_CACHE_SIZE, digest_cached
from fransys_model.layout import PoleGroup, layout_of
from fransys_model.vocab.tables import items
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Function, Item


@dataclasses.dataclass(frozen=True, slots=True)
class KeepWhole:
    """Each set is drawn together; sets are sorted, so the order is stable."""

    # Each non-harness item with children, with them: a coil with its add-on blocks.
    item_boxes: tuple[frozenset[Id[Item]], ...]
    # The functions of each `PoleGroup`: one multi-pole symbol.
    pole_groups: tuple[frozenset[Id[Function]], ...]
    # The items of each unit that holds an item drawn as a harness line.
    line_units: tuple[frozenset[Id[Item]], ...]


def _item_boxes(model: Model) -> tuple[frozenset[Id[Item]], ...]:
    """A parent that is no harness, with its children by `Item.parent`."""
    found = [
        frozenset({parent, *kids})
        for parent, kids in children_index(model).items()
        if not is_harness(model, parent)
    ]
    return tuple(sorted(found, key=sorted))


def _line_units(model: Model) -> tuple[frozenset[Id[Item]], ...]:
    """The members of each unit that holds a line owner, by `unit_index.items_of`."""
    table = items(model)
    held = {table[owner].unit for owner in line_conductors(model)}
    members = unit_index(model).items_of
    return tuple(sorted((members[unit] for unit in held if unit is not None), key=sorted))


@digest_cached(DIGEST_CACHE_SIZE)
def keep_whole_sets(model: Model) -> KeepWhole:
    """The `KeepWhole` sets of `model`: add-on item boxes, pole groups and units with a line.

    An item box is today approximated by "an item with children": the generic-box test lives in
    layout (`read/views.box_drawn`, needs the symbol rules) until EL-2 gives `function_role.box`.
    """
    groups = sorted(
        (frozenset(g.functions) for g in layout_of(model, PoleGroup).values()), key=sorted
    )
    return KeepWhole(_item_boxes(model), tuple(groups), _line_units(model))
