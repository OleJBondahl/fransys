"""The aspect nodes that are each unit's own, for every unit of a model in one pass (model-0067).

`designation.own_nodes` reads this. The rule is I4 R2 and F9, stated there; here it is computed
once per model, cached by digest, instead of once per unit over every item.
"""

import dataclasses
from typing import TYPE_CHECKING

from fransys_model.derive.lookups import effective_placement
from fransys_model.kernel import DIGEST_CACHE_SIZE, digest_cached, parent_chain
from fransys_model.vocab.cables import cable_items
from fransys_model.vocab.enums import Aspect
from fransys_model.vocab.membership import is_harness, item_chain, unit_subtree, units
from fransys_model.vocab.tables import aspect_nodes, items
from fransys_model.vocab.unit_index import unit_index

if TYPE_CHECKING:
    from collections.abc import Iterator

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.aspects import AspectNode
    from fransys_model.vocab.core import Item, Unit

# The two aspects a designation renders a segment for, each with its sign.
SIGNS = {Aspect.FUNCTION: "=", Aspect.LOCATION: "+"}


@dataclasses.dataclass(frozen=True, slots=True)
class UnitNodes:
    """Every unit's own aspect nodes, by unit id; a unit with none maps to the empty set."""

    own: frozendict[Id[Unit], frozenset[Id[AspectNode]]]


def chain_up(
    nodes: frozendict[Id[AspectNode], AspectNode], node_id: Id[AspectNode] | None
) -> Iterator[Id[AspectNode]]:
    """`node_id` and each ancestor above it, leaf first; a parent cycle ends the walk."""
    return parent_chain(lambda node: nodes[node].parent, node_id)


def outside_unit(model: Model, item: Id[Item], unit: Id[Unit] | None) -> bool:
    """Whether a list for `unit` names `item` from outside it; `unit=None` has no outside."""
    return unit is not None and items(model)[item].unit not in unit_subtree(model, unit)


def end_context(
    model: Model,
    item: Id[Item],
    node: Id[AspectNode] | None,
    context: Id[AspectNode] | None,
    unit: Id[Unit] | None,
) -> Id[AspectNode] | None:
    """`context`, or `None` (the whole path) for the end of `item` at `node` in a `unit` list.

    With a unit, an end inside `unit_subtree(unit)` prints short below `context`; an end outside
    it prints its whole path, even at the unit's location (model-0143: a unit knows only below).
    """
    if outside_unit(model, item, unit):
        return None
    if unit is None:
        return context
    return context if context in chain_up(aspect_nodes(model), node) else None


def _of_a_cable(model: Model, item: Id[Item], cables: set[Id[Item]]) -> bool:
    """Whether `item` is a cable, a harness or a member of one, by `Item.parent`."""
    return any(node in cables or is_harness(model, node) for node in item_chain(model, item))


def _reached(
    model: Model, containing: frozendict[Id[Unit], frozenset[Id[Unit]]]
) -> dict[Aspect, dict[Id[AspectNode], frozenset[Id[Unit]]]]:
    """Per aspect and node, the units every non-cable item reaching the node belongs to.

    An item reaches a node when the node is on the chain up from its `effective_placement`.
    An item in no unit empties the node's set; in the function aspect it is left out instead.
    """
    nodes = aspect_nodes(model)
    cables = set(cable_items(model))
    reached: dict[Aspect, dict[Id[AspectNode], frozenset[Id[Unit]]]] = {a: {} for a in SIGNS}
    for item in items(model).values():
        if _of_a_cable(model, item.id, cables):
            continue
        member_of = frozenset() if item.unit is None else containing.get(item.unit, frozenset())
        for aspect, table in reached.items():
            if aspect is Aspect.FUNCTION and item.unit is None:
                continue
            for node_id in chain_up(nodes, effective_placement(model, item.id, aspect)):
                prior = table.get(node_id)
                table[node_id] = member_of if prior is None else prior & member_of
    return reached


@digest_cached(DIGEST_CACHE_SIZE)
def _unit_nodes(model: Model) -> UnitNodes:
    """Compute `UnitNodes` in one pass over the items: `u` owns each node whose set holds `u`.

    `chain_up` follows `parent` across aspects: a node whose child is in another aspect is in both.
    The unit must hold it in both (an `ASPECT_CROSS_PARENT` model, `freeze` accepts it).
    """
    holders_by_node: dict[Id[AspectNode], frozenset[Id[Unit]]] = {}
    for table in _reached(model, unit_index(model).containing).values():
        for node_id, holders in table.items():
            prior = holders_by_node.get(node_id)
            holders_by_node[node_id] = holders if prior is None else prior & holders
    grouped: dict[Id[Unit], set[Id[AspectNode]]] = {unit: set() for unit in units(model)}
    for node_id, holders in holders_by_node.items():
        for unit in holders:
            grouped[unit].add(node_id)
    return UnitNodes(own=frozendict({unit: frozenset(found) for unit, found in grouped.items()}))


def own_nodes_by_unit(model: Model) -> frozendict[Id[Unit], frozenset[Id[AspectNode]]]:
    """Every unit's own aspect nodes, built once per model (I4 R2, F9; the rule is `own_nodes`').

    Cached on `model.digest`, holding the last few results: equal digests return the identical
    mapping. An unknown unit is not a key; ask through `own_nodes`, which refuses it.
    """
    return _unit_nodes(model).own
