"""`Env`: the model, the kit, the conventions and the id maps, built once and passed on."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fransys_model.derive import item_parents, port_designation

from .placement_ids import pin_names, symbol_ids, symbol_of
from .placement_kit import refuse

if TYPE_CHECKING:
    from fransys_layout.core import PinRef
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Function, Item, Port

    from .placement_kit import SymbolKit
    from .placement_options import Conventions

__all__ = ["Env", "make_env", "parent_map", "pin_ref"]


@dataclass(frozen=True, slots=True)
class Env:
    """What every part of the builder reads.

    `ids` maps a lead function to its symbol id, `owner` any drawn function to the symbol that
    draws it (a pole-group member to its lead's), `pins` a port to its `PinRef`.
    """

    model: Model
    kit: SymbolKit
    conventions: Conventions
    ids: frozendict[Id[Function], str]
    owner: frozendict[Id[Function], str]
    pins: frozendict[Id[Port], PinRef]
    parents: frozendict[Id[Item], Id[Item]]


def parent_map(model: Model) -> frozendict[Id[Item], Id[Item]]:
    """Each child item's parent item, read from `item_parents`, the one reader of a parent."""
    return item_parents(model)


def make_env(model: Model, kit: SymbolKit, conventions: Conventions) -> Env:
    """The ids and pins of `kit` over `model`; `ProblemError` for a pick that does not fit."""
    ids = symbol_ids(model, kit)
    pins = pin_names(model, kit, ids)
    return Env(model, kit, conventions, ids, symbol_of(kit, ids), pins, parent_map(model))


def pin_ref(env: Env, port: Id[Port]) -> PinRef:
    """The `PinRef` of `port`; `ProblemError` when its function has no pick in the kit."""
    found = env.pins.get(port)
    if found is None:
        text = port_designation(env.model, port)
        refuse(f"port {text}", "add a pick for its function to the SymbolKit")
    return found
