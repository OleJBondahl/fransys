"""The symbol adapter: what the engines read of the default library, and where a drawn symbol's ports meet their wires.

The symbols layer holds no electrical word; the library's text measure and port pitch, and the builder
of a drawn symbol, stay here. The one module besides `units.py` that imports the symbol libraries.
"""

from functools import partial
from typing import TYPE_CHECKING

import symdef

from electrical_symbols import LIBRARY, PORT_PITCH_G, drawn_symbol
from fransys_layout.symbols import fitted_marker
from fransys_layout.symbols import text_width_g as _grid_text_width

if TYPE_CHECKING:
    from fransys_layout.core.values import XY
    from fransys_layout.drawing import DrawnSymbol

__all__ = ("PORT_PITCH_G", "port_points", "text_width_g")

# a text's width on the grid in the library font: the symbols layer's one measure with the font bound
text_width_g = partial(_grid_text_width, LIBRARY.font)


def _turned(symbol: DrawnSymbol, library: symdef.Library) -> symdef.Symbol:
    """The library symbol `symbol` draws: texts, repeats, fitted slots, leads and turn applied.

    A stretched symbol is a marker: its slot is fitted to its text as placement fits it (R430.1).
    """
    made = drawn_symbol(
        symbol.key,
        symbol.texts,
        library=library,
        offsets=dict(symbol.offsets),
        sides=dict(symbol.sides),
    )
    built = symdef.repeat(made, symbol.poles, port_format=library.port_format) if symbol.poles > 1 else made
    for slot, text in symbol.slots if symbol.stretch else ():
        built = fitted_marker(built, slot, text, library)
    return symdef.orient(symdef.leads(built, symbol.leads), symdef.Orientation[symbol.orient])


def port_points(symbol: DrawnSymbol, library: symdef.Library) -> tuple[tuple[XY, str], ...]:
    """Each port of `symbol` as (its point on the page in G, its symdef port id), in port order.

    The symbol is built as placement measures it and measured at R0 (R391, R430.1), so each
    port sits where the drawing puts its wire end.
    """
    found = symdef.measure(_turned(symbol, library), symdef.Orientation.R0, library)
    return tuple(((symbol.x + p.x, symbol.y + p.y), p.id) for p in found.ports.values())
