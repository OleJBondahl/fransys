"""One symbol turned to each allowed orientation and measured, as the core's `Turned` views."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from symdef import GridBox, from_divisions, measure

from fransys_layout.core.errors import CoreError
from fransys_layout.core.sym_values import PinTurn, Turned
from fransys_layout.core.values import Box, Size

from ._grid import symdef_orientation, to_box
from .table import TableAsk, placed_table

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from symdef import Library

    from fransys_layout.core.values import Orientation

    from .shape import LibrarySymbol

__all__ = (
    "Ask",
    "Views",
    "symbol_views",
)


@dataclass(frozen=True, slots=True)
class Ask:
    """What to measure: the orientations, pin order, the text and its slot, and the extras.

    `order` lists the pin ids as the caller's `Sym.pins` run. `table` is a table made once,
    measured at each view and joined to its footprint; `strip` also gives each view its row
    footprint (the hull without the text slot). The text is measured at `text_height` G.
    """

    orientations: Sequence[Orientation]
    order: Sequence[str]
    text_slot: str
    text: str
    text_height: int
    table: TableAsk | None = None
    strip: bool = False


@dataclass(frozen=True, slots=True)
class Views:
    """The views of one symbol, its text slot's size at R0, and its table's keep-out at R0."""

    views: Mapping[Orientation, Turned]
    label: Size
    table: Box | None = None


def _view(
    symbol: LibrarySymbol,
    library: Library,
    orient: Orientation,
    ask: Ask,
    drawn: tuple[float, LibrarySymbol | None],
) -> tuple[Turned, Box | None, Box | None]:
    """The view at `orient`, its measured text slot's box and its table's keep-out box."""
    height, table = drawn
    turn = symdef_orientation(orient)
    bare = measure(symbol, turn, library)
    text = {ask.text_slot: ask.text} if ask.text_slot in {s.id for s in symbol.slots} else {}
    held = measure(symbol, turn, library, text or None, height)
    kept = None if table is None or orient != "R0" else measure(table, turn, library).keepout
    footprint = to_box(bare.keepout)
    others = [box for name, box in bare.slots.items() if name != ask.text_slot]
    row = to_box(GridBox.union(bare.body, *others)) if ask.strip else None
    ports = [bare.ports[p] for p in ask.order]
    pins = tuple(PinTurn(p.x, p.y, p.direction.name) for p in ports)
    slot = held.slots.get(next(iter(text), ""))
    view = Turned(to_box(bare.body), to_box(bare.keepout), footprint, pins, row)
    return view, None if slot is None else to_box(slot), None if kept is None else to_box(kept)


def symbol_views(symbol: LibrarySymbol, library: Library, ask: Ask) -> Views:
    """`symbol` at each orientation `ask` names, its text measured in the text slot."""
    if "R0" not in ask.orientations:
        msg = "the orientations hold no R0; every symbol is drawn at R0 first"
        raise CoreError(msg)
    height = from_divisions(library.grid, ask.text_height)
    table = None if ask.table is None else placed_table(ask.table, library, ask.text_height)
    found = {o: _view(symbol, library, o, ask, (height, table)) for o in ask.orientations}
    slot = found["R0"][1]
    return Views(
        {o: view for o, (view, _, _) in found.items()},
        Size(0, 0) if slot is None else Size(slot.w, slot.h),
        found["R0"][2],
    )
