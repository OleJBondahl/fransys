"""The power symbols of a core layout as `Drawing` values: the symbol and its lead (POWER-NET).

`write_power.power_symbols` decides each symbol, its turn and its origin; these draw its records
with no `layout.drawn_*` record: a `DrawnSymbol` at the origin and a `DrawnWire` from the pin to
the symbol's port.
"""

from typing import TYPE_CHECKING

from fransys_layout.drawing import DrawnSymbol, DrawnWire

from .drawn_identity import net_text, outline_of
from .drawn_ids import lead_id, symbol_id

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from fransys_layout.core import Anchored
    from fransys_model.kernel import Id, Model
    from fransys_model.layout import Page, PowerSymbol

__all__ = ["power_leads", "power_marks"]

_KEY = ("layout", "core")


def power_marks(records: Iterable[PowerSymbol]) -> Iterator[tuple[Id[Page], DrawnSymbol]]:
    """One symbol per power pin, at the origin the record gives, turned as it says."""
    for r in records:
        yield (
            r.page,
            DrawnSymbol(
                id=symbol_id(*_KEY, "drawn_power", *r.key[2:]),
                key=r.symbol,
                x=r.x,
                y=r.y,
                orient=r.orientation.name,
                outline=outline_of(r.symbol, r.orientation.name, r.x, r.y),
                ports=(r.port.value,),
            ),
        )


def power_leads(
    model: Model, records: Iterable[PowerSymbol], anchored: Iterable[Anchored]
) -> Iterator[tuple[Id[Page], str, DrawnWire]]:
    """One lead per power pin: the core's lead from the pin to the port of its symbol."""
    leads = {(a.sym, a.pin): a.lead for a in anchored}
    for r in records:
        wire_id = lead_id(*_KEY, "drawn_power_lead", *r.key[2:])
        points = leads[r.key[-2], r.key[-1]]
        yield (
            r.page,
            wire_id,
            DrawnWire(id=wire_id, points=points, style="wire", net=net_text(model, r.port)),
        )
