"""The unit an overview name prints relative to (O3, A3; model-0198), and a node's lines.

A thing prints relative to the innermost unit of the view's chain that holds it, so at
System / -U1 / -U2 a stub for an item of -U1 reads `-J1`, not `-U1-J1`. Reached through `derive`.
"""

from fransys_model.vocab.tables import aspect_nodes, items
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.aspects import AspectNode
lazy from fransys_model.vocab.core import Item, Unit

from .designation import location_node_designation
from .lookups import unit_chain

__all__ = ["display_unit", "node_lines"]


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


def node_lines(model: Model, node: Id[AspectNode]) -> tuple[str, ...]:
    """An aspect node's printed lines: its designation, then its description; none when empty."""
    text = (location_node_designation(model, node), aspect_nodes(model)[node].description)
    return tuple(line for line in text if line)
