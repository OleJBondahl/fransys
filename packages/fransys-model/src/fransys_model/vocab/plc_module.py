"""Whether an item is a PLC module: the one part-category test of what a rack holds.

Lives in `vocab`, not `derive`, because a validator reads it and `vocab` never imports `derive`.
"""

lazy from fransys_model.kernel import Model

from .enums import PartCategory
from .tables import parts
lazy from .core import Item


def is_plc_module(model: Model, item: Item) -> bool:
    """Whether `item`'s part has category `PLC_MODULE`: the one test of what a rack holds.

    A rack is an item with at least one such child; `plc_rack_modules` lists them.
    """
    return item.part is not None and parts(model)[item.part].category is PartCategory.PLC_MODULE
