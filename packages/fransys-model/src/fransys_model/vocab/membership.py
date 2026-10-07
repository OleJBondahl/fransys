"""Unit, board and harness membership (units spec U8, decisions model-0040 and model-0043).

`units`, `unit_subtree`, `unit_items`, `standalone`, `boundary`, `item_chain`,
`enclosing_boards`, `external`, `unit_own_roots`, `is_sole_unit_root`, `in_reading`,
`cable_children` and
`is_harness`, plus `require`, the identity refusal that `derive.lookups` re-exports
(`derive.external` re-exports `external`). Every per-unit and per-item fact reads the per-model
index of `vocab.unit_index`, built once per model digest, never a scan of the items table
(decision model-0067). Lives in `vocab`, not `derive`, because `vocab.validators` read them and
a layer imports only the layers to its right (`derive` -> `layout` -> `vocab` -> `kernel`,
design/foundations.md 4).
"""

from typing import TYPE_CHECKING, Any

from fransys_model.kernel import Id, Model, SchemaError, parent_chain

from .tables import items
from .tables import units as units_table
from .unit_index import unit_index
lazy from .core import Function, Item, Unit

if TYPE_CHECKING:
    from collections.abc import Iterator


def require[R](found: R | None, kind: str, target: Id[Any]) -> R:
    """`found`, or the refusal every query gives for an identity id the model does not hold."""
    if found is None:
        msg = f"the id is not a {kind} of the model"
        raise SchemaError(msg, kind=kind, record_id=target)
    return found


def units(model: Model) -> tuple[Id[Unit], ...]:
    """Every `Unit` id in `model`, in `Id` order (units spec U8)."""
    return tuple(sorted(units_table(model)))


def unit_subtree(model: Model, unit: Id[Unit]) -> frozenset[Id[Unit]]:
    """`unit` and every unit whose `parent` chain reaches it.

    Cycle-safe, like `derive.structure.subtree`. Reads the per-model unit index.

    Raises:
        SchemaError: `unit` is not a unit of `model`.
    """
    require(units_table(model).get(unit), "unit", unit)
    return unit_index(model).subtree_of[unit]


def unit_items(model: Model, unit: Id[Unit]) -> frozenset[Id[Item]]:
    """Every item of `model` whose `unit` is in `unit_subtree(model, unit)`.

    Reads the per-model unit index.

    Raises:
        SchemaError: `unit` is not a unit of `model`.
    """
    require(units_table(model).get(unit), "unit", unit)
    return unit_index(model).items_of[unit]


def standalone(model: Model, unit: Id[Unit]) -> bool:
    """Whether every item of `model` belongs to `unit`'s subtree.

    A unit is standalone when nothing in `model` sits outside it: no item with `unit=None`
    and no item of another unit that is not in `unit`'s own subtree.

    Raises:
        SchemaError: `unit` is not a unit of `model`.
    """
    require(units_table(model).get(unit), "unit", unit)
    # `items_of[unit]` is a subset of the items table, so equal sizes mean equal sets.
    return len(unit_index(model).items_of[unit]) == len(items(model))


def boundary(model: Model, unit: Id[Unit]) -> tuple[Id[Function], ...]:
    """The functions that are part of `unit`'s interface, in `Id` order.

    One function may be `unit`'s boundary through more than one `Boundary` record; it is
    listed once.

    Raises:
        SchemaError: `unit` is not a unit of `model`.
    """
    require(units_table(model).get(unit), "unit", unit)
    return unit_index(model).boundary_of[unit]


def item_chain(model: Model, item: Id[Item]) -> Iterator[Id[Item]]:
    """`item` and each ancestor above it by `Item.parent`, leaf first; a `parent` cycle ends it.

    A lazy `kernel.parent_chain` walk: an unknown `item` raises `KeyError` once advanced past.
    Every walk up `Item.parent` in `vocab` and `derive` reads this one.
    """
    all_items = items(model)
    return parent_chain(lambda node: all_items[node].parent, item)


def enclosing_boards(model: Model, item: Id[Item]) -> tuple[Id[Item], ...]:
    """`item` and its ancestors by `Item.parent` that carry a `pcb` facet, outermost first.

    `item` itself is included when it is one. Cycle-safe: a `parent` cycle ends the walk.
    The board parts come from the per-model unit index. The one predicate every board-membership
    question in this repo answers: `derive.designation.designating_ancestors` (item
    designations, excluding `item` itself; it walks boards and harnesses alike),
    `vocab.validators.connectivity`'s board-realised rule (DESIGN
    8: a net needs no conductors when one board is common to every port's item, intersecting
    `frozenset(enclosing_boards(...))` over the net's ports), `derive.structure.
    schematic_functions` (a function on or under a board item, board-relative walk), and
    layout's board-internal connection rule -- one walk, so a drawn
    connector can never fail to count as its own board's by one copy drifting from another.
    """
    board_part_ids = unit_index(model).pcb_parts
    all_items = items(model)
    boards = (node for node in item_chain(model, item) if all_items[node].part in board_part_ids)
    return tuple(reversed(tuple(boards)))


def external(model: Model, item: Id[Item]) -> bool:
    """Whether `item` is external: it, or any item on its `parent` chain, has `external=True`.

    The terminals of an external strip and the modules of an external rack are therefore
    external without each carrying the flag. `installed` is a separate fact and is not read.
    A `parent` cycle ends the walk (`validators.structure` reports it as `CONTAINMENT_CYCLE`).
    Reads the per-model unit index.

    Raises:
        SchemaError: `item` is not an item of `model`.
    """
    require(items(model).get(item), "item", item)
    return item in unit_index(model).external


def unit_own_roots(model: Model, unit: Id[Unit]) -> tuple[Id[Item], ...]:
    """`unit`'s own root items, in the items table's order: the one definition.

    An own item (`Item.unit == unit`) whose `parent` is `None` or in another unit; not external.
    Its callers share it, so a board's `-U2` on its parent's BOM and its own set's silence agree.
    """
    return unit_index(model).own_roots.get(unit, ())


def is_sole_unit_root(model: Model, item: Id[Item]) -> bool:
    """Whether `item` is the only own-root item of its own unit.

    `False` when `item.unit` is `None`. Otherwise `True` only when `unit_own_roots` of that
    unit is exactly `(item,)` (external items are not roots): a board
    that is the *whole* content of its own `Unit` is a nested unit, not a
    board sitting inside a larger one -- and a board sitting inside a larger unit still carries
    that larger unit on itself and on everything nested under it via `parent=`, so "shares a
    unit with an ancestor board" cannot tell the two cases apart; only "is the sole root of its
    unit" can. `enclosing_boards` above answers "which board (if any) encloses this item";
    this answers "is that board a whole unit on its own, or merely furniture inside one".

    Raises:
        SchemaError: `item` is not an item of `model`.
    """
    all_items = items(model)
    found = require(all_items.get(item), "item", item)
    if found.unit is None:
        return False
    return unit_own_roots(model, found.unit) == (item,)


def cable_children(model: Model, item: Id[Item]) -> tuple[Id[Item], ...]:
    """`item`'s direct children by `Item.parent` that are a cable (`is_cable`), in `Id` order.

    The one place that reads which children are cables; `is_harness` reads it, so they agree.
    A caller that renders sorts its own output; an item the model does not hold has none.
    """
    return unit_index(model).cable_children.get(item, ())


def is_harness(model: Model, item: Id[Item]) -> bool:
    """Whether `item` is a harness: any child by `Item.parent` is a cable (`is_cable`).

    A harness is a plain `Item` whose children say so: no record kind, no new facet.
    A container with no cable child reads flat, whatever else it holds (a rack, a strip).
    """
    return bool(cable_children(model, item))


def in_unit_subtree(model: Model, item: Id[Item], unit: Id[Unit]) -> bool:
    """Whether `item`'s unit is `unit` or a unit nested under it; an item in no unit is not.

    An unknown `unit` is refused like `unit_subtree` refuses it.
    """
    return items(model)[item].unit in unit_subtree(model, unit)


def in_reading(model: Model, item: Id[Item], unit: Id[Unit] | None) -> bool:
    """Whether `item` lies inside a reading's subject (model-0157): `unit=None` is any unit.

    A given `unit` reads its subtree (`in_unit_subtree`); an item in no unit is never inside.
    The one rule behind CD4's end order and CD5's rows.
    """
    if unit is None:
        return items(model)[item].unit is not None
    return in_unit_subtree(model, item, unit)


def crosses_unit(model: Model, one: Id[Item], other: Id[Item]) -> bool:
    """Whether the two items lie in different units, strictly (model-0152).

    A sub-unit is a different unit from its parent, so a nested unit's item crosses against
    the parent's. An item in no unit differs from one in a unit, and equals another in none.
    """
    all_items = items(model)
    return all_items[one].unit != all_items[other].unit
