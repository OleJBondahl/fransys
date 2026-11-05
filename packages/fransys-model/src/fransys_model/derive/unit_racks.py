"""The racks of a unit: the one reader behind the export of a WAGO file per rack (model-0280)."""

from fransys_model.vocab.tables import items
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Item, Unit

from .order import plc_racks

__all__ = ["unit_racks"]


def unit_racks(model: Model, unit: Id[Unit] | None) -> tuple[Id[Item], ...]:
    """The racks (`plc_racks`) of `unit`, id-sorted; every rack for `unit=None`."""
    all_items = items(model)
    racks = plc_racks(model)
    return tuple(rack for rack in all_items if rack in racks and (unit is None or all_items[rack].unit == unit))
