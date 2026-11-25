"""`Env`: the model, kit, conventions, build library and id maps, built once and passed on."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fransys_model.derive import (
    board_of_ports,
    boundary,
    enclosing_boards,
    far_pins,
    function_item,
    item_of_port,
    item_parents,
    port_designation,
    schematic_functions,
    unit_ids,
)
from fransys_model.derive.order import plc_module_ranks

from .kit_keys import function_of, held_ports, hidden_box_ports
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
    from fransys_model.vocab import Function, Item, Port

    from .placement_kit import SymbolKit
    from .placement_options import Conventions

__all__ = ["Env", "drawn_pins", "make_env", "pin_ref", "refuse_inside_board"]


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
    ranks: frozendict[PickKey, int] = frozendict()
    boundary: frozenset[Id[Function]] = frozenset()


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
        (undrawn_pins(model) - set(pins)) | {p for k in spare for p in held_ports(model, k)} | hidden_box_ports(model, kit),
        spare,
        _ranks(model, ids),
        frozenset(f for u in unit_ids(model) for f in boundary(model, u)),
    )


def drawn_pins(env: Env, ports: Iterable[Id[Port]]) -> tuple[PinRef, ...]:
    """The `PinRef` of each of `ports` a symbol draws: an undrawn connector pin has none."""
    return tuple(pin_ref(env, p) for p in ports if p not in env.undrawn)


def _wired_out_of_its_board(env: Env, port: Id[Port], owner: Id[Function]) -> bool:
    """Whether `port`, a pin of a board's own function that is no interface pin, has a conductor to a port outside the board."""
    item = item_of_port(env.model, port)
    if not enclosing_boards(env.model, item) or owner in schematic_functions(env.model):
        return False
    return any(board_of_ports(env.model, pair) is None for pair in far_pins(env.model, [port]))


def refuse_inside_board(env: Env, ports: Iterable[Id[Port]]) -> None:
    """`ProblemError` when a pin of a board's own function is wired out of the board: a board is a black box (R2627)."""
    for port in ports:
        owner = function_of(env.model, port)
        if _wired_out_of_its_board(env, port, owner):
            refuse(f"port {port_designation(env.model, port)}", "wire a connector of its board: a board is a black box", symbol_key(env.model, owner))


def pin_ref(env: Env, port: Id[Port]) -> PinRef:
    """The `PinRef` of `port`; `ProblemError` when its function has no pick in the kit."""
    found = env.pins.get(port)
    if found is None:
        text = port_designation(env.model, port)
        owner = function_of(env.model, port)
        refuse(f"port {text}", "add a pick for its function to the SymbolKit", symbol_key(env.model, owner))
    return found
