"""The texts and the place of each coil's contact table head (R339, R345).

The core's annex stage places the head; this is the one home of its place and its drawn symbol.
"""

from dataclasses import replace
from typing import TYPE_CHECKING

from electrical_symbols import drawn_slots
from fransys_layout.core import Box
from fransys_layout.drawing import Drawing, DrawnSymbol, DrawnText
from fransys_layout.symbols import line_pitch, text_room_on, text_width_g
from fransys_model.derive import coil_table_texts, contact_places, function_placements, function_role
from fransys_model.derive.order import in_place_order
from fransys_model.layout import Page, layout_of, sheet_format_of

from .drawn_ids import core_symbol_id, symbol_id
from .drawn_where import where_text
from .kit_keys import function_of
from .placement_ids import symbol_key
from .placement_tables import is_table_spot

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping, Sequence

    from electrical_symbols import Library
    from fransys_layout.core import CoreLayout
    from fransys_model.kernel import Id, Model
    from fransys_model.layout import FrameCell
    from fransys_model.vocab import Function

    from .placement_kit import SymbolKit

__all__ = ["HEAD", "head_places", "place_texts", "table_heads", "table_texts"]

_KEY = ("layout", "core")
_TERMINAL = "terminal"
HEAD = "contact-head"


def table_texts(model: Model, kit: SymbolKit) -> Mapping[str, tuple[tuple[str, ...], ...]]:
    """The texts of every lead's table, by symbol id."""
    return {symbol_key(model, f): coil_table_texts(model, function_of(model, f)) for f in kit}


def head_places(layout: CoreLayout, texts: Mapping[str, tuple[tuple[str, ...], ...]]) -> Iterator[tuple[int, str, Box]]:
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


def _placed(model: Model, owner: Mapping[str, Id[Function]], sym: DrawnSymbol, page: Id[Page]) -> DrawnSymbol:
    """`sym` with its entries given their placed places when it is a table head, else `sym`."""
    if sym.key != HEAD or sym.id not in owner:
        return sym
    coil = owner[sym.id]
    texts = coil_table_texts(model, coil, contact_places(model, coil, page))
    return replace(sym, texts=texts, slots=tuple(drawn_slots(HEAD, texts).items()))


def _lines(model: Model, on: tuple[Library, int], text: DrawnText, rows: Sequence[tuple[Id[Page], FrameCell]], page: Id[Page]) -> list[DrawnText]:
    """The where lines under the tag `text`: one per placement of its terminal off `page`, each one line pitch after the last.

    A turned tag reads bottom-up, so its lines stack to the right, each its own thickness wide, from the tag's start.
    """
    library, height = on
    here = next((r for r in rows if r[0] == page), None)
    if here is None:
        return []
    step, lines = line_pitch(library, height), [where_text(model, here, there) for there in rows if there[0] != page]
    found = []
    for i, line in enumerate(lines):
        width = text_width_g(library.font, line, height=height)
        if text.turned:
            box = Box(text.box.x + step * (i + 1), text.box.y + text.box.h - width, height, width)
        else:
            box = Box(text.box.x, text.box.y + step * (i + 1), width, height)
        found.append(DrawnText(line, box, "WHERE", "SW" if text.turned else "NW", text.owner, text.turned))
    return found


def _where(model: Model, kit: SymbolKit, library: Library, drawings: Mapping[Id[Page], Drawing]) -> dict[Id[Page], tuple[DrawnText, ...]]:
    """The where-text under each tag of a placed terminal: one line per other placement (R1397, R1571).

    `where_text` of each other placement, from the Membership rows, one line below the last.
    """
    rows = function_placements(model)
    owner = {core_symbol_id(symbol_key(model, f)): function_of(model, f) for f in kit}
    found: dict[Id[Page], tuple[DrawnText, ...]] = {}
    pages = layout_of(model, Page)
    for page, drawing in drawings.items():
        height = text_room_on(model, sheet_format_of(model, pages[page].sheet_format), library)
        drawn = {sym.id for sym in drawing.symbols if sym.key == _TERMINAL}
        tagged = [(t, owner.get(t.owner or "")) for t in drawing.texts if t.owner in drawn]
        found[page] = tuple(
            line
            for t, f in tagged
            if f is not None and function_role(model, f).terminal
            for line in _lines(model, (library, height), t, rows.get(f, ()), page)
        )
    return found


def place_texts(model: Model, kit: SymbolKit, library: Library, drawings: Mapping[Id[Page], Drawing]) -> dict[Id[Page], Drawing]:
    """`drawings` with every text that names another placement: a table head's entries and a terminal's where-text.

    Placement reserves a stand-in width; once every set is laid, the places are in `model`'s
    `layout.membership` rows; `contact_places` gives each contact's text on the head's page.
    """
    owner = {symbol_id(*_KEY, "drawn_table", symbol_key(model, f)): function_of(model, f) for f in kit}
    where = _where(model, kit, library, drawings)
    return {
        page: replace(
            drawing,
            symbols=tuple(_placed(model, owner, sym, page) for sym in drawing.symbols),
            texts=in_place_order((t.box.y, t.box.x, t) for t in (*drawing.texts, *where[page])),
        )
        for page, drawing in drawings.items()
    }
