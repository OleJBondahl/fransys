"""The core `Anchor` of each stand pin: its power symbol's turn, origin and outline per pin side.

Read once from the symdef layer (SB11); the core moves the values and knows no power kind.
"""

from typing import TYPE_CHECKING, cast

from electrical_symbols import WIRING_GRID, power_symbol_key
from fransys_layout import Facing, symbol_geometry
from fransys_layout.core import SIDE_STEP, Anchor, Box, PinRef, Pose
from fransys_layout.symbols import library_symbol, measured_slots
from fransys_model.derive import port_power_text, stands
from fransys_model.derive.order import functions_in_order
from fransys_model.layout import Orientation

from .placement_ids import symbol_key
from .placement_kit import refuse

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from electrical_symbols import Library
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Function, Port

    from .placement_kit import SymbolKit

__all__ = ["anchors_of", "stood"]

_TURNS = tuple(Orientation)[:4]
# (quarter turns round the pin side, reach in steps): straight out first, then along the owner;
# the deeper straight-out reaches stagger the symbols of pins closer than one outline
_APPROACHES = (
    (0, 1),
    (0, 2),
    (1, 1),
    (3, 1),
    (1, 2),
    (3, 2),
    (1, 3),
    (3, 3),
    (0, 3),
    (0, 4),
    (0, 5),
    (0, 6),
)
_AROUND = tuple(Facing)  # clockwise from N, so two on is the opposite


def stood(model: Model, kit: SymbolKit) -> Iterator[tuple[str, str, Id[Port], str]]:
    """(symbol id, pin name, port, `PowerKind` value) of each pick port on a power net."""
    power = stands(model)
    for function in cast("tuple[Id[Function], ...]", functions_in_order(model, kit)):
        pick = kit[function]
        for port in cast("tuple[Id[Port], ...]", functions_in_order(model, pick.ports)):
            if port in power:  # the pins of one symbol in model port-name order, so the fit never depends on the Id salt
                yield symbol_key(model, function), pick.ports[port], port, power[port].value


def _pose(key: str, side: Facing, quarter: int, reach: int, keeps: Mapping[Orientation, Box]) -> Pose:
    """The turn of `key` whose port faces a pin `reach` steps off, `quarter` turns round `side`.

    Its box is `keeps` at that turn: the keep-out with the rail's text measured into its slot.
    """
    out = _AROUND[(_AROUND.index(side) + quarter) % len(_AROUND)]
    back = _AROUND[(_AROUND.index(out) + 2) % len(_AROUND)]
    for turn in _TURNS:
        geometry = symbol_geometry(key, orientation=turn)
        port = geometry.ports[0]
        if port.facing is back:
            sx, sy = SIDE_STEP[out.name]
            dx, dy = sx * reach * WIRING_GRID - port.at.x, sy * reach * WIRING_GRID - port.at.y
            b = keeps[turn]
            box = Box(b.x + dx, b.y + dy, b.w, b.h)
            return Pose(turn.name, (dx, dy), box, (sx * reach * WIRING_GRID, sy * reach * WIRING_GRID))
    msg = f"symbol {key!r} has no turn whose port faces {back.name}; use a one-port symbol"
    return refuse(f"symbol {key}", msg)


def _keeps(model: Model, key: str, port: Id[Port], library: Library, height: int) -> dict[Orientation, Box]:
    """The keep-out of `key` at each turn, the text of `port` measured into its slot (TEXT-BOX-MEASURED); `height` is the text height in G."""
    text = port_power_text(model, port)
    symbol = library_symbol(library, key)
    found = {}
    for turn in _TURNS:
        slot = f"marking.{symbol_geometry(key, orientation=turn).ports[0].name}"
        found[turn] = measured_slots(symbol, turn.name, {slot: text} if text else {}, library, height)[1]
    return found


def anchors_of(model: Model, kit: SymbolKit, library: Library, height: int) -> tuple[Anchor, ...]:
    """One `Anchor` per stand pin, in kit order; `height` is the text height in G."""
    found = []
    for sym_id, name, port, kind in stood(model, kit):
        key = power_symbol_key(kind)
        keeps = _keeps(model, key, port, library, height)
        poses = tuple((side.name, _pose(key, side, q, r, keeps)) for side in Facing for q, r in _APPROACHES)
        found.append(Anchor(PinRef(sym_id, name), poses))
    return tuple(found)
