"""The unit a name in an overview view is printed relative to (O3, A3; model-0198).

A thing prints relative to the innermost unit of the view's chain that holds it, so at
System / -U1 / -U2 a stub for an item of -U1 reads `-J1`, not `-U1-J1`. Reached through `derive`.
"""

from fransys_model.vocab.tables import items
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Item, Unit

from .lookups import unit_chain

__all__ = ["display_unit"]


def display_unit(model: Model, item: Id[Item], unit: Id[Unit] | None) -> Id[Unit] | None:
    """The unit `item` prints relative to in the view of `unit`: its innermost opened holder.

    `unit` is the unit whose level the view draws, `None` for the system. An item no opened unit
    holds, or in no unit, prints as the view's own unit does.
    """
    owner = items(model)[item].unit
    if unit is None or owner is None:
        return unit
    held = set(unit_chain(model, owner))
    return next((one for one in unit_chain(model, unit) if one in held), unit)
