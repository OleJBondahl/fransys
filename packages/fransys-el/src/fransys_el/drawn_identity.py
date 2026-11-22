"""The outline and identity strings a `Drawing` carries that render ignores (DRAWING-INVARIANTS).

`outline_of` is a library symbol's body at a page position; `ports_of` the ports each symbol draws;
`net_text` the identity of a port's drawn net (as `Net.id`).
"""

from dataclasses import replace
from typing import TYPE_CHECKING, Literal, cast

from electrical_symbols import drawn_symbol
from fransys_layout.core import Box, CoreError
from fransys_layout.symbols import library_symbol, stretched_body, turned_view
from fransys_model.derive import drawn_net_of

from .placement_ids import net_key, pin_names, symbol_ids

if TYPE_CHECKING:
    from collections.abc import Mapping

    from electrical_symbols import Library
    from fransys_layout.core import Orientation
    from fransys_layout.drawing import Drawing, DrawnSymbol
    from fransys_layout.symbols import LibrarySymbol
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Port

    from .placement_kit import SymbolKit

__all__ = ["built_symbol", "ink_of", "inked", "net_text", "outline_of", "ports_of"]


def outline_of(key: str, orient: str, x: int, y: int, library: Library) -> Box:
    """The body of library symbol `key` turned to `orient`, with its origin at (x, y) in G."""
    body = turned_view(library_symbol(library, key), library, cast("Orientation", orient)).body
    return Box(x + body.x, y + body.y, body.w, body.h)


def built_symbol(symbol: DrawnSymbol, library: Library) -> LibrarySymbol:
    """The library symbol a drawn record draws: its texts, offsets, sides and turn applied, its poles repeated."""
    if symbol.texts:
        return drawn_symbol(symbol.key, symbol.texts, library=library, offsets=dict(symbol.offsets), sides=dict(symbol.sides), turn=symbol.turn)
    return library_symbol(library, symbol.key, symbol.poles)


def ink_of(symbol: DrawnSymbol, library: Library) -> Box:
    """The body symdef measures of the symbol as drawn, stretched to its record's lengths and turned, at its place (W4: the reader reads ink)."""
    built = built_symbol(symbol, library)
    if other := [a for a, _ in symbol.stretch if a not in {"x", "y"}]:
        msg = f"symbol {symbol.id!r} stretches along {other[0]!r}; a stretch axis is x or y"
        raise CoreError(msg)
    lengths: Mapping[Literal["x", "y"], int] = {cast("Literal['x', 'y']", a): n for a, n in symbol.stretch}
    body = stretched_body(built, symbol.orient, lengths, library)
    return Box(symbol.x + body.x, symbol.y + body.y, body.w, body.h)


def inked(drawing: Drawing, library: Library) -> Drawing:
    """`drawing` with each symbol's outline the ink symdef measures of it, not the box the writer stamped: the reader reads ink."""
    return replace(drawing, symbols=tuple(replace(s, outline=ink_of(s, library)) if s.outline is not None else s for s in drawing.symbols))


def ports_of(model: Model, kit: SymbolKit) -> dict[str, tuple[str, ...]]:
    """For each symbol id, the values of the ports it draws, in the kit's order."""
    found: dict[str, list[str]] = {}
    for port, pin in pin_names(model, kit, symbol_ids(model, kit)).items():
        found.setdefault(pin.sym, []).append(port.value)
    return {sym: tuple(ports) for sym, ports in found.items()}


def net_text(model: Model, port: Id[Port]) -> str:
    """The identity of `port`'s drawn net (`drawn_net_of`, a bridge joins none), spelled as `Net.id` is (`net_key`); `""` for a port in none.

    The reader spells every drawn net from `drawn_net_of`, as the wires of the core do (el-0136).
    """
    net = drawn_net_of(model, port)
    return net_key(model, net.ports) if net else ""
