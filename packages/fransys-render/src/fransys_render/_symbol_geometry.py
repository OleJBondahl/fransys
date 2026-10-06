"""The D6 recipe: `LIBRARY.get` -> `repeat` -> `orient`, for one placement's symbol."""

from typing import TYPE_CHECKING

from graphical_symbols import Orientation as LibraryOrientation
from graphical_symbols import UnknownSymbolError, orient, repeat

from electrical_symbols import GENERIC_BOX_KEY, LIBRARY, generic_box
from fransys_model.derive import build_indexes
from fransys_model.layout import PlacementView
from fransys_model.vocab import functions, ports

if TYPE_CHECKING:
    from graphical_symbols.model import Symbol

    from fransys_model.kernel import Model
    from fransys_model.layout import Orientation, PowerSymbol, SymbolPlacement

__all__ = ["GENERIC_BOX_KEY", "oriented_power_symbol", "oriented_symbol", "to_grid"]


def to_grid(module_units: float) -> int:
    """One coordinate, module units to grid units (0.125 M each): exact, no rounding."""
    return int(module_units * 8)


def _generic_box_port_names(model: Model, placement: SymbolPlacement) -> tuple[str, ...]:
    """The placement's function's model port names, sorted (R7 B2)."""
    indexes = build_indexes(model)
    if placement.ports:  # the item view's own list, as layout drew it
        return placement.ports
    if placement.view is PlacementView.ITEM:
        item = functions(model)[placement.function].item
        return tuple(
            sorted(
                f"{function.name}.{ports(model)[port_id].name}"
                for function in functions(model).values()
                if function.item == item
                for port_id in indexes.ports_by_function.get(function.id, ())
            )
        )
    port_ids = indexes.ports_by_function.get(placement.function, ())
    return tuple(sorted(ports(model)[port_id].name for port_id in port_ids))


def oriented_symbol(model: Model, placement: SymbolPlacement) -> Symbol | None:
    """`placement`'s symbol, repeated and oriented as layout drew it; `None` for an unknown key."""
    if placement.symbol == GENERIC_BOX_KEY:
        # R7 C5: the port sides layout turned the box to, else the alternating ones
        base = generic_box(
            _generic_box_port_names(model, placement),
            tuple(side.value for side in placement.sides),
            tuple(offset / 8 for offset in placement.port_offsets),  # grid units to M
        )
    else:
        try:
            base = LIBRARY.get(placement.symbol)
        except UnknownSymbolError:
            return None
    if placement.poles > 1:
        base = repeat(base, placement.poles)
    return _turned(base, placement.orientation)


def oriented_power_symbol(power: PowerSymbol) -> Symbol:
    """`power`'s library symbol turned to its orientation: the one draw path of a placement."""
    return _turned(LIBRARY.get(power.symbol), power.orientation)


def _turned(base: Symbol, orientation: Orientation) -> Symbol:
    """`base` oriented by the model's `Orientation`, converted by member name."""
    return orient(base, LibraryOrientation[orientation.value.upper()])
