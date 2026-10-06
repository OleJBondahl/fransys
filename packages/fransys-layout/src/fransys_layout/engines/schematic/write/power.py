"""Private to `write/`: the `PowerSymbol` builder (D5, model-0117).

A marker the stages flagged as a power end is written as a `PowerSymbol`, never a `LinkMarker`;
its text is an ordinary `MARKING` label of its port (`labels.labels`).
"""

from dataclasses import replace
from typing import TYPE_CHECKING, Any

from fransys_layout.engines.schematic.write.keys import PREFIX
from fransys_layout.stages.texts.power import power_places
from fransys_model.kernel import make_id
from fransys_model.layout import PowerSymbol

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.engines.schematic.engine import StageResults
    from fransys_layout.engines.schematic.write.keys import PageId, WriteKeys
    from fransys_layout.stages import Layout
    from fransys_model.kernel import AuthoringKey, Id
    from fransys_model.layout import Page


def without_power(layout: Layout) -> Layout:
    """`layout` with the power ends out of its markers: the link markers' builder sees the rest."""
    return replace(layout, markers=tuple(one for one in layout.markers if not one.symbol))


def power_symbols(
    keys: WriteKeys,
    results: StageResults,
    page_of: Mapping[PageId, Page],
    discriminator: Mapping[tuple[Id[Any], int, int], AuthoringKey],
    stamp: str,
) -> list[PowerSymbol]:
    """One `PowerSymbol` per power port and page, keyed by the port and its placement."""
    owner_of = {
        port.port: function.function for function in results.drawn for port in function.ports
    }
    records = []
    for one in power_places(results.layout.markers):
        where = discriminator[owner_of[one.port], one.drawing_set, one.page]
        key = (*PREFIX, "power_symbol", *keys.port[one.port], *where)
        records.append(
            PowerSymbol(
                id=make_id(PowerSymbol, key),
                key=key,
                port=one.port,
                page=page_of[one.drawing_set, one.page].id,
                symbol=one.symbol,
                x=one.at.x,
                y=one.at.y,
                pin_x=one.pin.x,
                pin_y=one.pin.y,
                orientation=one.orientation,
                produced_by=stamp,
            )
        )
    return records
