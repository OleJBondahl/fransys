"""The page `Drawing` values straight from a `CoreLayout` (FLIP-NOW F7).

`draw_set` builds one drawing set's symbols, wires and texts.
`finish_drawings` adds the reference markers.

Transitional residue: the marker text and `#n` are `fransys_model.derive` functions that
read `LinkMarker` records. `finish_drawings` puts the in-memory markers, built as `link_markers`
builds them, into a scratch model that it never returns or stores. When those functions take
plain values this residue goes.
"""

from dataclasses import replace
from typing import TYPE_CHECKING

from electrical_symbols import library_version
from fransys_layout.core import Box
from fransys_layout.drawing import Drawing, DrawnOutline, DrawnSymbol, DrawnText, DrawnWire
from fransys_layout.symbols import library_symbol, measured_slots, text_room_on, text_width_g
from fransys_model.derive import build_indexes, ordered_pages
from fransys_model.derive.order import in_place_order
from fransys_model.kernel import evolve
from fransys_model.layout import sheet_format_of

from .draw_outlines import drawn_outlines
from .draw_power import power_leads, power_marks
from .draw_symbols import junction_dots, placed_symbols
from .drawn_identity import ports_of
from .drawn_ids import core_symbol_id, wire_id
from .drawn_texts import box_rows
from .kit_keys import tag_of
from .placement_ids import symbol_key
from .placement_kit import refuse
from .placement_nets import net_ports
from .placement_options import sheet_area
from .placement_sets import frame_units
from .placement_tables import is_table_spot
from .read_markers import drawn_marker
from .write_markings import marking_slots
from .write_power import power_symbols
from .write_tables import table_heads, table_texts
from .write_texts import symbol_keys

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Mapping

    from electrical_symbols import Library
    from fransys_layout.core import Wire
    from fransys_model.kernel import Id, Model, Origin
    from fransys_model.layout import LinkMarker, Page

    from .placement_kit import PickKey
    from .write_pages import Written

__all__ = ["draw_set", "finish_drawings"]

_KEY = ("layout", "core")


def _wires(wires: Iterable[Wire], model: Model, pages: Mapping[int, Page], number: int) -> list[tuple[Id[Page], DrawnWire]]:
    """One wire per core wire of drawing set `number`; the set number is in the id.

    A wire's port on two nets is refused: a net can have wires in two sets, a port is on one net.
    """
    lead_of, nets_of = net_ports(model), build_indexes(model).nets_by_port
    found = []
    for i, w in enumerate(wires):
        lead = lead_of.get(w.net)
        if lead is not None and len(nets_of.get(lead, ())) > 1:
            refuse(f"port {w.net}", f"is on {len(nets_of[lead])} nets; put it on one net")
        style = "trunk" if w.lane is not None else "wire"
        found.append((pages[w.page].id, DrawnWire(id=wire_id(number, w.net, i), points=tuple(w.points), style=style, net=w.net)))
    return found


def _place(item: DrawnSymbol | DrawnWire | DrawnText) -> tuple[int, int]:
    """The (y, x) an element draws at: a wire at its first point."""
    if isinstance(item, DrawnWire):
        x, y = item.points[0]
        return y, x
    if isinstance(item, DrawnText):
        return item.box.y, item.box.x
    return item.y, item.x


def _in_place_order[T: DrawnSymbol | DrawnWire | DrawnText](
    found: Iterable[tuple[Id[Page], T]],
) -> dict[Id[Page], tuple[T, ...]]:
    """The things by page, each page's top-down and left to right (`in_place_order`)."""
    pages: dict[Id[Page], list[T]] = {}
    for page, item in found:
        pages.setdefault(page, []).append(item)
    return {page: in_place_order((*_place(item), item) for item in items) for page, items in pages.items()}


def _labels(w: Written, keys: Mapping[str, PickKey]) -> list[tuple[Id[Page], DrawnText]]:
    """One TAG text per core label, anchored NW at the label's box (CORE-TEXTS A)."""
    layout, model, pages, unit = w.layout, w.model, w.pages, w.within
    found = []
    for label in (a for a in layout.annotations.annexes if not is_table_spot(a.spot)):
        if label.owner not in keys or label.page not in pages:
            refuse(
                f"label of {label.owner} on page {label.page}",
                "the label's symbol or page is not in the written layout: pass the build's kit",
                label.owner,
            )
        page = pages[label.page]
        # the house label's em in G: its capital height over the font's ratio (E10)
        height = text_room_on(model, sheet_format_of(model, page.sheet_format), w.library)
        text = tag_of(model, keys[label.owner], unit=unit)
        box = Box(label.box.x, label.box.y, text_width_g(w.library.font, text, height=height), height)
        found.append((page.id, DrawnText(text, box, "TAG", "NW", core_symbol_id(label.owner))))
    return found


def _inked(w: Written, items: Iterable[tuple[Id[Page], DrawnSymbol]]) -> Iterator[tuple[Id[Page], DrawnSymbol]]:
    """Each symbol with the page box symdef measures around the strings in its slots (TEXT-BOX-MEASURED)."""
    by_id = {p.id: p for p in w.pages.values()}
    for page, s in items:
        if not s.slots or s.stretch or s.texts:  # a stretched symbol or a table fits its slots to its text already
            yield page, s
            continue
        height = text_room_on(w.model, sheet_format_of(w.model, by_id[page].sheet_format), w.library)
        boxes, _ = measured_slots(library_symbol(w.library, s.key, s.poles), s.orient, dict(s.slots), w.library, height)
        ink = tuple((slot, Box(boxes[slot].x + s.x, boxes[slot].y + s.y, boxes[slot].w, boxes[slot].h)) for slot, _ in s.slots if slot in boxes)
        yield page, replace(s, slot_ink=ink)


def draw_set(w: Written) -> dict[Id[Page], Drawing]:
    """The drawing of each page of one set of `unit`, without its reference markers.

    Symbols, wires and texts draw top-down, left to right, so no id decides the bytes (NUMBER-SORT).
    """
    model, layout, kit, pages = w.model, w.layout, w.kit, w.pages
    ports = ports_of(model, kit)
    shown = {(sym := symbol_key(model, f)): (pick.key, box_rows(pick), pick.poles, ports.get(sym, ())) for f, pick in kit.items()}
    marks = {symbol_key(model, f): marking_slots(model, pick, w.library) for f, pick in kit.items()}
    texts_of = table_texts(model, kit)
    wires = tuple(w for page in layout.routes.pages for w in page.wires)
    powers = power_symbols(model, layout, pages, kit, ("", w.owner.number))
    symbols = _in_place_order(
        _inked(
            w,
            (
                *placed_symbols(layout, w.problem, pages, shown, marks),
                *table_heads(layout, pages, texts_of),
                *junction_dots(layout, pages),
                *power_marks(model, powers, w.library),
            ),
        )
    )
    texts = _in_place_order(_labels(w, symbol_keys(model, kit)))
    frames: dict[Id[Page], tuple[DrawnOutline, ...]] = {}
    for page, outline in drawn_outlines(model, layout, pages, frame_units(model, kit), w.library):
        frames[page] = (*frames.get(page, ()), outline)
    drawn = _in_place_order((*_wires(wires, model, pages, w.owner.number), *power_leads(model, powers, layout.annotations.anchored)))
    return {
        page.id: Drawing(
            area=sheet_area(sheet_format_of(model, page.sheet_format)),
            symbols=symbols.get(page.id, ()),
            wires=drawn.get(page.id, ()),
            texts=texts.get(page.id, ()),
            outlines=frames.get(page.id, ()),
            library_version=library_version(),
        )
        for page in pages.values()
    }


def finish_drawings(
    laid: Model,
    drawn: Mapping[Id[Page], Drawing],
    markers: Iterable[LinkMarker],
    origin: Origin,
    library: Library,
) -> dict[Id[Page], Drawing]:
    """The drawings of `laid`'s pages with their markers in.

    The pages come in the order they print. `laid` holds the pages; the markers are put into a
    scratch copy only (the residue named in the module docstring).
    """
    markers = tuple(markers)
    scratch = evolve(laid, put=markers, origin=origin)
    marks = [drawn_marker(scratch, marker, library) for marker in markers]
    by_page = _in_place_order((m.page, s) for m, s in zip(markers, marks, strict=True))
    found: dict[Id[Page], Drawing] = {}
    for page in ordered_pages(scratch):
        if page.id in drawn:
            old = drawn[page.id]
            found[page.id] = Drawing(
                old.area,
                (*old.symbols, *by_page.get(page.id, ())),
                old.wires,
                old.texts,
                old.outlines,
                old.library_version,
            )
    return found
