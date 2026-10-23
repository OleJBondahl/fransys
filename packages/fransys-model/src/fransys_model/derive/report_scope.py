"""Which unit a record belongs to: the scope tests every list shares.

Direct membership only, never a nested unit's; see design/derive-queries.md.
"""

from fransys_model.vocab.enums import ConductorKind
from fransys_model.vocab.tables import items
from fransys_model.vocab.tables import units as units_table
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.connectivity import Conductor
lazy from fransys_model.vocab.core import Item, Unit

from .lookups import item_of_port, require, unit_chain
from .structure import boards
from .wiring import terminal_strips


def _require_unit(model: Model, unit: Id[Unit] | None) -> None:
    """Refuse `unit` if it names no `Unit` of `model`; `None` is always fine."""
    if unit is not None:
        require(units_table(model).get(unit), "unit", unit)


def _item_belongs(model: Model, item_id: Id[Item], unit: Id[Unit]) -> bool:
    """Whether `item_id` is directly a member of `unit`: `item.unit == unit`.

    Direct membership only, never `unit_subtree`: an item of a nested unit belongs to that
    nested unit alone, never to its ancestor.
    """
    return items(model)[item_id].unit == unit


def unit_strips(model: Model, unit: Id[Unit]) -> tuple[Id[Item], ...]:
    """The terminal strips `unit` owns directly, in designation order, never a nested unit's.

    The strips of `terminal_strips` whose `item.unit` is `unit`; one test of a unit's own strips.
    """
    return tuple(strip for strip in terminal_strips(model) if _item_belongs(model, strip, unit))


def unit_boards(model: Model, unit: Id[Unit]) -> tuple[Id[Item], ...]:
    """The boards `unit` owns directly, in designation order, never a nested unit's.

    The boards of `boards` whose `item.unit` is `unit`; the one test of a unit's own boards.
    """
    return tuple(board for board in boards(model) if _item_belongs(model, board, unit))


def _lowest_common_unit(model: Model, a: Id[Unit] | None, b: Id[Unit] | None) -> Id[Unit] | None:
    """The lowest unit whose subtree holds both `a` and `b`; `None` if either is `None`.

    Either end with no unit at all means the conductor belongs to no unit.
    """
    if a is None or b is None:
        return None
    if a == b:
        return a
    chain_b = set(unit_chain(model, b))
    return next((candidate for candidate in unit_chain(model, a) if candidate in chain_b), None)


def _conductor_unit(model: Model, conductor: Conductor) -> Id[Unit] | None:
    """The unit `conductor` belongs to, or `None`.

    A `core` conductor belongs to its cable item's own unit, never computed from its ends.
    Any other belongs to the lowest unit whose subtree holds both ends' items.
    """
    if conductor.kind is ConductorKind.CORE and conductor.carrier is not None:
        return items(model)[conductor.carrier].unit
    a_unit = items(model)[item_of_port(model, conductor.a)].unit
    b_unit = items(model)[item_of_port(model, conductor.b)].unit
    return _lowest_common_unit(model, a_unit, b_unit)


def _conductor_belongs(model: Model, conductor: Conductor, unit: Id[Unit]) -> bool:
    """Whether `conductor` belongs to `unit`: `_conductor_unit(...) == unit`."""
    return _conductor_unit(model, conductor) == unit
