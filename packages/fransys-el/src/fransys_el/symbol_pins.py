"""The connector-pin picks of the symbol kit: one symbol per drawn pin view, keyed by its port.

The pins are `derive.connector_pin_views`; whether a pin is drawn, and its mate, are the view's.
The symbol is the connector's choice (`symbol_rules`, at the connector's gender), made once per
function by the caller. A pin binds its one port to the symbol's one port, or the port map's.
"""

from typing import TYPE_CHECKING

from fransys_layout.symbols import library_symbol
from fransys_model.derive import connected_ports, connector_pin_views

from .placement_kit import Pick, refuse
from .symbol_bind import Shape, Target, port_of

if TYPE_CHECKING:
    from collections.abc import Mapping
    from collections.abc import Set as AbstractSet

    from electrical_symbols import Library
    from fransys_model.derive import PinView
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Function, Port

__all__ = ["Choice", "pin_picks", "undrawn_pins"]

_ALONE = Shape(1, (), {})

type Choice = tuple[str | None, frozendict[str, str]]


def _pick(library: Library, view: PinView, choice: Choice) -> Pick:
    """The pick of one drawn pin: the connector's symbol, its port bound at the pin's name."""
    symbol, port_map = choice
    if symbol is None:
        refuse(f"connector pin {view.name}", "no symbol rule names a connector pin: add one")
    ports = {p.id for p in library_symbol(library, symbol, 1).ports}
    chosen = port_of(view.name, _ALONE, port_map, Target(ports, {}, 1))
    if chosen not in ports:
        refuse(f"connector pin {view.name}", f"no port of symbol {symbol} to bind it to")
    return Pick(symbol, 1, frozendict({view.port: chosen}))


def pin_picks(
    model: Model,
    library: Library,
    wired: AbstractSet[Id[Port]],
    choices: Mapping[Id[Function], Choice],
) -> dict[Id[Port], Pick]:
    """One pick per drawn pin view, by its port. No device chain keeps a connector whole here."""
    rows = connector_pin_views(model, frozenset(), frozenset(wired))
    return {row.port: _pick(library, row, choices[row.function]) for row in rows if row.drawn}


def undrawn_pins(model: Model) -> frozenset[Id[Port]]:
    """The connector pins no view draws: a net or mate end there has no symbol to land on."""
    rows = connector_pin_views(model, frozenset(), connected_ports(model))
    return frozenset(row.port for row in rows if not row.drawn)
