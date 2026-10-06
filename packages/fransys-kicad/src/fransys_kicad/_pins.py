"""What a netlist `node` says about a port: its component reference and pad number."""

from typing import TYPE_CHECKING

from fransys_model.derive import item_designation, item_of_port
from fransys_model.vocab import ports

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Item, Port


def pin_of(
    model: Model, designations: dict[Id[Item], str], port: Id[Port], board: Id[Item]
) -> tuple[str, str]:
    """`port`'s reference and pad by ids, never parsed; no part row: board-relative (model-0040)."""
    item = item_of_port(model, port)
    ref = (
        designations[item]
        if item in designations
        else item_designation(model, item, relative_to=board)
    )
    return ref, ports(model)[port].name
