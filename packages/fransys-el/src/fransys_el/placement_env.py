"""`Env`: the model, kit, conventions, build library and id maps, built once and passed on."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fransys_model.derive import (
    function_ports,
    item_parents,
    port_designation,
    schematic_functions,
)

from .kit_keys import held_ports
from .placement_ids import pin_names, symbol_ids, symbol_key, symbol_of
from .placement_kit import refuse
from .placement_spares import spare_leads
from .symbol_pins import undrawn_pins
lazy from .kit_keys import PickKey

if TYPE_CHECKING:
    from collections.abc import Iterable

    from electrical_symbols import Library
    from fransys_layout.core import PinRef
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Item, Port

    from .placement_kit import SymbolKit
    from .placement_options import Conventions

__all__ = ["Env", "drawn_pins", "make_env", "parent_map", "pin_ref"]


@dataclass(frozen=True, slots=True)
class Env:
    """What every part of the builder reads.

    `ids` maps a lead function to its symbol id, `owner` any drawn function to the symbol that
    draws it (a pole-group member to its lead's), `pins` a port to its `PinRef`.
    """

    model: Model
    kit: SymbolKit
    conventions: Conventions
    library: Library
    ids: frozendict[PickKey, str]
    owner: frozendict[PickKey, str]
    pins: frozendict[Id[Port], PinRef]
    parents: frozendict[Id[Item], Id[Item]]
    undrawn: frozenset[Id[Port]]
    spare: frozendict[PickKey, str] = frozendict()


def parent_map(model: Model) -> frozendict[Id[Item], Id[Item]]:
    """Each child item's parent item, read from `item_parents`, the one reader of a parent."""
    return item_parents(model)


def make_env(model: Model, kit: SymbolKit, conventions: Conventions, library: Library) -> Env:
    """The ids and pins of `kit` over `model`; `ProblemError` for a pick that does not fit."""
    ids = symbol_ids(model, kit)
    pins = pin_names(model, kit, ids)
    spare = spare_leads(model, kit, ids, pins)
    if spare:  # a spare terminal is listed, not drawn (R356)
        kit = frozendict({k: v for k, v in kit.items() if k not in spare})
        ids = frozendict({k: v for k, v in ids.items() if k not in spare})
        pins = pin_names(model, kit, ids)
    return Env(
        model,
        kit,
        conventions,
        library,
        ids,
        symbol_of(kit, ids),
        pins,
        parent_map(model),
        (undrawn_pins(model) - set(pins)) | {p for k in spare for p in held_ports(model, k)},
        spare,
    )


def drawn_pins(env: Env, ports: Iterable[Id[Port]]) -> tuple[PinRef, ...]:
    """The `PinRef` of each of `ports` a symbol draws: an undrawn connector pin has none."""
    return tuple(pin_ref(env, p) for p in ports if p not in env.undrawn)


def pin_ref(env: Env, port: Id[Port]) -> PinRef:
    """The `PinRef` of `port`; `ProblemError` when its function has no pick in the kit."""
    found = env.pins.get(port)
    if found is None:
        text = port_designation(env.model, port)
        owner = next(
            f for f in schematic_functions(env.model) if port in function_ports(env.model, f)
        )
        key = symbol_key(env.model, owner)
        refuse(f"port {text}", "add a pick for its function to the SymbolKit", key)
    return found
