"""The outline and identity strings a `Drawing` carries that render ignores (DRAWING-INVARIANTS).

`outline_of` is a library symbol's body at a page position; `ports_of` the ports each symbol draws;
`net_text` the identity of a port's physical net, the value of its first port (as `Net.id`).
"""

from typing import TYPE_CHECKING, cast

from fransys_layout.core import Box
from fransys_layout.symbols import library_symbol, turned_view
from fransys_model.derive import net_of

from .placement_ids import net_key, pin_names, symbol_ids

if TYPE_CHECKING:
    from electrical_symbols import Library
    from fransys_layout.core import Orientation
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Port

    from .placement_kit import SymbolKit

__all__ = ["net_text", "outline_of", "ports_of"]


def outline_of(key: str, orient: str, x: int, y: int, library: Library) -> Box:
    """The body of library symbol `key` turned to `orient`, with its origin at (x, y) in G."""
    body = turned_view(library_symbol(library, key), library, cast("Orientation", orient)).body
    return Box(x + body.x, y + body.y, body.w, body.h)


def ports_of(model: Model, kit: SymbolKit) -> dict[str, tuple[str, ...]]:
    """For each symbol id, the values of the ports it draws, in the kit's order."""
    found: dict[str, list[str]] = {}
    for port, pin in pin_names(model, kit, symbol_ids(model, kit)).items():
        found.setdefault(pin.sym, []).append(port.value)
    return {sym: tuple(ports) for sym, ports in found.items()}


def net_text(model: Model, port: Id[Port]) -> str:
    """The identity of `port`'s physical net, spelled as `Net.id` is (`net_key`); `""` for none."""
    net = net_of(model, port)
    return net_key(model, net.ports) if net else ""
