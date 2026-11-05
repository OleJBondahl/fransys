"""`Env`: the model, kit, conventions, build library and id maps, built once and passed on."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fransys_model.derive import (
    function_item,
    item_parents,
    port_designation,
    schematic_functions,
)
from fransys_model.derive.order import plc_module_ranks

from .kit_keys import function_of, held_ports
from .placement_ids import pin_names, symbol_ids, symbol_key, symbol_of
from .placement_kit import refuse
from .placement_spares import spare_leads
from .placement_where import where_line
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

__all__ = ["Env", "drawn_pins", "make_env", "pin_ref", "port_pins"]


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
    where: str
    spare: frozendict[PickKey, str] = frozendict()
    ranks: frozendict[PickKey, int] = frozendict()


def _ranks(model: Model, ids: Iterable[PickKey]) -> frozendict[PickKey, int]:
    """Each symbol's rank: a PLC module by its rack place, then the rest as `functions_in_order` gave `ids`; no Id text decides (SYMBOL-TIE)."""
    plc = plc_module_ranks(model)
    modules = {k: plc[i] for k in ids if (i := function_item(model, function_of(model, k))) in plc}
    rest = (k for k in ids if k not in modules)
    return frozendict({**modules, **{k: len(plc) + n for n, k in enumerate(rest)}})


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
        item_parents(model),
        (undrawn_pins(model) - set(pins)) | {p for k in spare for p in held_ports(model, k)},
        where_line(model, library, len(ids)),
        spare,
        _ranks(model, ids),
    )


def port_pins(model: Model, kit: SymbolKit, conventions: Conventions, library: Library) -> frozendict[Id[Port], PinRef]:
    """The `PinRef` each drawn port of `model` stands at: `Env.pins`, the one map `build` reads.

    A port with no entry is undrawn (an undrawn connector pin, a spare lead). Raises `ProblemError` as `build` does.
    """
    return make_env(model, kit, conventions, library).pins


def drawn_pins(env: Env, ports: Iterable[Id[Port]]) -> tuple[PinRef, ...]:
    """The `PinRef` of each of `ports` a symbol draws: an undrawn connector pin has none."""
    return tuple(pin_ref(env, p) for p in ports if p not in env.undrawn)


def pin_ref(env: Env, port: Id[Port]) -> PinRef:
    """The `PinRef` of `port`; `ProblemError` when its function has no pick in the kit."""
    found = env.pins.get(port)
    if found is None:
        text = port_designation(env.model, port)
        owner = function_of(env.model, port)
        key = symbol_key(env.model, owner)
        if owner in schematic_functions(env.model):
            refuse(f"port {text}", "add a pick for its function to the SymbolKit", key)
        refuse(f"port {text}", "wire a connector of its board: a board is a black box", key)
    return found
