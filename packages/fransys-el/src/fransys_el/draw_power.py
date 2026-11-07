"""The power symbols of a core layout as `Drawing` values: the symbol and its lead (POWER-NET).

`write_power.power_symbols` decides each symbol, its turn and its origin; these draw its records
with no `layout.drawn_*` record: a `DrawnSymbol` at the origin and a `DrawnWire` from the pin to
the symbol's port.
"""

from typing import TYPE_CHECKING

from fransys_layout.drawing import DrawnSymbol, DrawnWire
from fransys_layout.symbols import library_symbol
from fransys_model.derive import port_power_text

from .drawn_identity import net_text, outline_of
from .drawn_ids import lead_id, symbol_id

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from electrical_symbols import Library
    from fransys_layout.core import Anchored
    from fransys_model.kernel import Id, Model
    from fransys_model.layout import Page, PowerSymbol

__all__ = ["power_leads", "power_marks"]

_KEY = ("layout", "core")


def _supply_text(model: Model, r: PowerSymbol, library: Library) -> tuple[tuple[str, str], ...]:
    """(`marking.<its port>`, the rail's text) when the net prints one and the symbol declares that slot (G08-POWER)."""
    text = port_power_text(model, r.port)
    symbol = library_symbol(library, r.symbol)
    named = {f"marking.{port.id}" for port in symbol.ports}
    return tuple((slot.id, text) for slot in symbol.slots if slot.id in named) if text else ()


def power_marks(model: Model, records: Iterable[PowerSymbol], library: Library) -> Iterator[tuple[Id[Page], DrawnSymbol]]:
    """One symbol per power pin, at the origin the record gives, turned as it says, with its rail's text."""
    for r in records:
        yield (
            r.page,
            DrawnSymbol(
                id=symbol_id(*_KEY, "drawn_power", *r.key[2:]),
                key=r.symbol,
                x=r.x,
                y=r.y,
                orient=r.orientation.name,
                slots=_supply_text(model, r, library),
                outline=outline_of(r.symbol, r.orientation.name, r.x, r.y, library),
                ports=(r.port.value,),
            ),
        )


def power_leads(model: Model, records: Iterable[PowerSymbol], anchored: Iterable[Anchored]) -> Iterator[tuple[Id[Page], DrawnWire]]:
    """One lead per power pin: the core's lead from the pin to the port of its symbol."""
    leads = {(a.sym, a.pin): a.lead for a in anchored}
    for r in records:
        wire_id = lead_id(*_KEY, "drawn_power_lead", *r.key[2:])
        points = leads[r.key[-2], r.key[-1]]
        yield r.page, DrawnWire(id=wire_id, points=points, style="wire", net=net_text(model, r.port))
