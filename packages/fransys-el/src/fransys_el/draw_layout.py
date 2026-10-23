"""The page `Drawing` values and reference links straight from a `CoreLayout` (FLIP-NOW F7).

`draw_set` builds one drawing set's symbols, wires and texts.
`finish_drawings` adds the reference markers and the links.

Transitional residue: the marker text, `#n` and links are `fransys_model.derive` functions that
read `LinkMarker` records. `finish_drawings` puts the in-memory markers, built as `link_markers`
builds them, into a scratch model that it never returns or stores. When those functions take
plain values this residue goes.
"""

from typing import TYPE_CHECKING

from electrical_symbols import G_PER_MODULE, library_version
from fransys_layout.core import Box, Size
from fransys_layout.drawing import Drawing, DrawnText, DrawnWire
from fransys_model.derive import build_indexes, ordered_pages
from fransys_model.derive.order import record_id_order
from fransys_model.derive.page_nav import reference_links
from fransys_model.derive.text_width import text_width
from fransys_model.kernel import evolve
from fransys_model.layout import sheet_format_of

from .draw_power import power_leads, power_marks
from .draw_symbols import junction_dots, placed_symbols
from .drawn_ids import core_symbol_id, text_id, wire_id
from .kit_keys import tag_of
from .placement_kit import refuse
from .placement_tables import is_table_spot
from .read_markers import drawn_marker
from .read_texts import label_height
from .write_power import power_symbols
from .write_tables import table_heads, table_texts

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from electrical_symbols import Library
    from fransys_layout.core import CoreLayout, PlacementProblem, Wire
    from fransys_model.derive.page_nav import ReferenceLink
    from fransys_model.kernel import Id, Model, Origin
    from fransys_model.layout import LinkMarker, Page
    from fransys_model.vocab import Unit

    from .placement_kit import PickKey, SymbolKit

__all__ = ["draw_set", "finish_drawings"]

_KEY = ("layout", "core")


def _area(model: Model, page: Page) -> Size:
    """The page's content box in G: its sheet's content mm over one grid division."""
    sheet = sheet_format_of(model, page.sheet_format)
    per_mm = G_PER_MODULE / sheet.module_mm
    return Size(int(sheet.content_width_mm * per_mm), int(sheet.content_height_mm * per_mm))


def _wires(
    wires: Iterable[Wire], model: Model, pages: Mapping[int, Page], number: int
) -> list[tuple[Id[Page], str, DrawnWire]]:
    """One wire per core wire of drawing set `number`; the set number is in the id.

    A wire's port on two nets is refused: a net can have wires in two sets, a port is on one net.
    """
    by_value = {port.value: nets for port, nets in build_indexes(model).nets_by_port.items()}
    found = []
    for i, w in enumerate(wires):
        if len(by_value.get(w.net, ())) > 1:
            refuse(f"port {w.net}", f"is on {len(by_value[w.net])} nets; put it on one net")
        wire = wire_id(number, w.net, i)
        found.append(
            (
                pages[w.page].id,
                wire,
                DrawnWire(
                    id=wire,
                    points=tuple(w.points),
                    style="trunk" if w.lane is not None else "wire",
                    net=w.net,
                ),
            )
        )
    return found


def _in_record_order[T](
    found: Iterable[tuple[Id[Page], str, T]],
) -> dict[Id[Page], tuple[T, ...]]:
    """The things by page, each page's in the record path's order (`record_id_order`)."""
    by_id = {item_id: (page, item) for page, item_id, item in found}
    pages: dict[Id[Page], list[T]] = {}
    for item_id in record_id_order(by_id):
        page, item = by_id[item_id]
        pages.setdefault(page, []).append(item)
    return {page: tuple(items) for page, items in pages.items()}


def _labels(
    layout: CoreLayout,
    model: Model,
    keys: Mapping[str, PickKey],
    pages: Mapping[int, Page],
    unit: Id[Unit] | None,
) -> list[tuple[Id[Page], str, DrawnText]]:
    """One TAG text per core label, anchored NW at the label's box (CORE-TEXTS A)."""
    found = []
    for label in (a for a in layout.annotations.annexes if not is_table_spot(a.spot)):
        if label.owner not in keys or label.page not in pages:
            refuse(
                f"label of {label.owner} on page {label.page}",
                "the label's symbol or page is not in the written layout: pass the build's kit",
                label.owner,
            )
        page = pages[label.page]
        height = label_height(model, sheet_format_of(model, page.sheet_format))
        text = tag_of(model, keys[label.owner], unit=unit)
        box = Box(label.box.x, label.box.y, text_width(text, height=height), height)
        found.append(
            (
                page.id,
                text_id("TAG", label.owner),
                DrawnText(text, box, "TAG", "NW", core_symbol_id(label.owner)),
            )
        )
    return found


def draw_set(  # noqa: PLR0913 - the set's layout, model, kit and symbol facts join its pages
    model: Model,
    layout: CoreLayout,
    problem: PlacementProblem,
    kit: SymbolKit,
    pages: Mapping[int, Page],
    *,
    number: int,
    shown: Mapping[str, tuple[str, tuple[tuple[str, ...], ...], int, tuple[str, ...]]],
    marks: Mapping[str, Mapping[str, str]],
    keys: Mapping[str, PickKey],
    unit: Id[Unit] | None,
) -> dict[Id[Page], Drawing]:
    """The drawing of each page of one set of `unit`, without its reference markers.

    Symbols, wires and texts keep the record path's order, so the bytes stay identical.
    """
    texts_of = table_texts(model, kit)
    wires = tuple(w for page in layout.routes.pages for w in page.wires)
    powers = power_symbols(model, layout, pages, kit, "")
    symbols = _in_record_order(
        (page, s.id, s)
        for page, s in (
            *placed_symbols(layout, problem, pages, shown, marks),
            *table_heads(layout, pages, texts_of),
            *junction_dots(layout, pages),
            *power_marks(powers),
        )
    )
    texts = _in_record_order(_labels(layout, model, keys, pages, unit))
    drawn = _in_record_order(
        (
            *_wires(wires, model, pages, number),
            *power_leads(model, powers, layout.annotations.anchored),
        )
    )
    return {
        page.id: Drawing(
            area=_area(model, page),
            symbols=symbols.get(page.id, ()),
            wires=drawn.get(page.id, ()),
            markers=(),
            texts=texts.get(page.id, ()),
            outlines=(),
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
) -> tuple[dict[Id[Page], Drawing], dict[Id[Page], tuple[ReferenceLink, ...]]]:
    """The drawings of `laid`'s pages with their markers in, and each page's reference links.

    The pages come in the order they print. `laid` holds the pages; the markers are put into a
    scratch copy only (the residue named in the module docstring).
    """
    markers = tuple(markers)
    scratch = evolve(laid, put=markers, origin=origin)
    marks = [drawn_marker(scratch, marker, library) for marker in markers]
    by_page = _in_record_order((m.page, s.id, s) for m, s in zip(markers, marks, strict=True))
    found: dict[Id[Page], Drawing] = {}
    links: dict[Id[Page], tuple[ReferenceLink, ...]] = {}
    for page in ordered_pages(scratch):
        if page.id in drawn:
            old = drawn[page.id]
            found[page.id] = Drawing(
                old.area,
                (*old.symbols, *by_page.get(page.id, ())),
                old.wires,
                (),
                old.texts,
                (),
                old.library_version,
            )
            links[page.id] = reference_links(scratch, page.id, frozenset(drawn))
    return found, links
