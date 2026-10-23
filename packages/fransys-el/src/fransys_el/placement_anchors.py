"""The core `Anchor` of each stand pin: its power symbol's turn, origin and outline per pin side.

Read once from the symdef layer (SB11); the core moves the values and knows no power kind.
"""

from typing import TYPE_CHECKING

from electrical_symbols import WIRING_GRID, power_symbol_key
from fransys_layout import Facing, symbol_geometry
from fransys_layout.core import Anchor, Box, PinRef, Pose
from fransys_model.derive import stands
from fransys_model.layout import Orientation

from .placement_ids import symbol_key
from .placement_kit import refuse

if TYPE_CHECKING:
    from collections.abc import Iterator

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Port

    from .placement_kit import SymbolKit

__all__ = ["anchors_of", "stood"]

# y grows down (the `Facing` contract), so N steps towards smaller y.
_STEP = {Facing.N: (0, -1), Facing.E: (1, 0), Facing.S: (0, 1), Facing.W: (-1, 0)}
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
    for function, pick in kit.items():
        for port, name in pick.ports.items():
            if port in power:
                yield symbol_key(model, function), name, port, power[port].value


def _pose(key: str, side: Facing, quarter: int, reach: int) -> Pose:
    """The turn of `key` whose port faces a pin `reach` steps off, `quarter` turns round `side`."""
    out = _AROUND[(_AROUND.index(side) + quarter) % len(_AROUND)]
    back = _AROUND[(_AROUND.index(out) + 2) % len(_AROUND)]
    for turn in _TURNS:
        geometry = symbol_geometry(key, orientation=turn)
        port = geometry.ports[0]
        if port.facing is back:
            sx, sy = _STEP[out]
            dx, dy = sx * reach * WIRING_GRID - port.at.x, sy * reach * WIRING_GRID - port.at.y
            b = geometry.body
            box = Box(b.x + dx, b.y + dy, b.width, b.height)
            return Pose(
                turn.name, (dx, dy), box, (sx * reach * WIRING_GRID, sy * reach * WIRING_GRID)
            )
    msg = f"symbol {key!r} has no turn whose port faces {back.name}; use a one-port symbol"
    return refuse(f"symbol {key}", msg)


def anchors_of(model: Model, kit: SymbolKit) -> tuple[Anchor, ...]:
    """One `Anchor` per stand pin, in kit order."""
    found = []
    for sym_id, name, _port, kind in stood(model, kit):
        key = power_symbol_key(kind)
        poses = tuple(
            (side.name, _pose(key, side, q, r)) for side in Facing for q, r in _APPROACHES
        )
        found.append(Anchor(PinRef(sym_id, name), poses))
    return tuple(found)
