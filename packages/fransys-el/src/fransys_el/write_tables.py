"""The texts and the place of each coil's contact table head (R339, R345).

The core's annex stage places the head; this is the one home of its place and its drawn symbol.
"""

from dataclasses import replace
from typing import TYPE_CHECKING

from electrical_symbols import drawn_slots
from fransys_layout.drawing import Drawing, DrawnSymbol
from fransys_model.derive import coil_table_texts, contact_places

from .drawn_ids import symbol_id
from .kit_keys import function_of
from .placement_ids import symbol_key
from .placement_tables import is_table_spot

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from fransys_layout.core import Box, CoreLayout
    from fransys_model.kernel import Id, Model
    from fransys_model.layout import Page
    from fransys_model.vocab import Function

    from .placement_kit import SymbolKit

__all__ = ["HEAD", "head_places", "place_heads", "table_heads", "table_texts"]

_KEY = ("layout", "core")
HEAD = "contact-head"


def table_texts(model: Model, kit: SymbolKit) -> Mapping[str, tuple[tuple[str, ...], ...]]:
    """The texts of every lead's table, by symbol id."""
    return {symbol_key(model, f): coil_table_texts(model, function_of(model, f)) for f in kit}


def head_places(
    layout: CoreLayout, texts: Mapping[str, tuple[tuple[str, ...], ...]]
) -> Iterator[tuple[int, str, Box]]:
    """(page number, symbol id, box) of each table head the core's annex stage placed."""
    for item in layout.annotations.annexes:
        if is_table_spot(item.spot) and texts.get(item.owner):
            yield item.page, item.owner, item.box


def table_heads(
    layout: CoreLayout,
    pages: Mapping[int, Page],
    texts: Mapping[str, tuple[tuple[str, ...], ...]],
) -> Iterator[tuple[Id[Page], DrawnSymbol]]:
    """One head `Drawing` symbol per placed table."""
    for page, sym, box in head_places(layout, texts):
        yield (
            pages[page].id,
            DrawnSymbol(
                id=symbol_id(*_KEY, "drawn_table", sym),
                key=HEAD,
                x=box.x,
                y=box.y,
                orient="R0",
                slots=tuple(drawn_slots(HEAD, texts[sym]).items()),
                texts=texts[sym],
                outline=box,
            ),
        )


def _placed(
    model: Model, owner: Mapping[str, Id[Function]], sym: DrawnSymbol, page: Id[Page]
) -> DrawnSymbol:
    """`sym` with its entries given their placed places when it is a table head, else `sym`."""
    if sym.key != HEAD or sym.id not in owner:
        return sym
    coil = owner[sym.id]
    texts = coil_table_texts(model, coil, contact_places(model, coil, page))
    return replace(sym, texts=texts, slots=tuple(drawn_slots(HEAD, texts).items()))


def place_heads(
    model: Model, kit: SymbolKit, drawings: Mapping[Id[Page], Drawing]
) -> dict[Id[Page], Drawing]:
    """`drawings` with each table head's entries given their placed places (C2.4).

    Placement reserves a stand-in width; once every set is laid, the places are in `model`'s
    `layout.membership` rows; `contact_places` gives each contact's text on the head's page.
    """
    owner = {
        symbol_id(*_KEY, "drawn_table", symbol_key(model, f)): function_of(model, f) for f in kit
    }
    return {
        page: replace(
            drawing, symbols=tuple(_placed(model, owner, sym, page) for sym in drawing.symbols)
        )
        for page, drawing in drawings.items()
    }
