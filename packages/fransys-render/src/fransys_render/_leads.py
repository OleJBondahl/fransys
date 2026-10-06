"""Bound-lead visibility (spec TL3, decision render-0002)."""

from dataclasses import replace
from typing import TYPE_CHECKING

from graphical_symbols.geometry import Line

from fransys_model.kernel import DIGEST_CACHE_SIZE, digest_cached
from fransys_model.layout import Label, LabelKind, LinkMarker, Route, layout_of, page_slice
from fransys_model.layout import Page as PageRecord
from fransys_model.vocab import ports

from ._symbol_geometry import to_grid

if TYPE_CHECKING:
    from graphical_symbols.model import Symbol

    from fransys_model.kernel import Id, Model
    from fransys_model.layout import Page, SymbolPlacement
    from fransys_model.vocab import Function

type _Grid = tuple[int, int]
type _Ends = tuple[frozenset[_Grid], frozenset[_Grid]]
_NO_ENDS: _Ends = (frozenset[_Grid](), frozenset[_Grid]())

# A MARKING label's `slot` is `marking.<symbol port name>` (fransys_layout's labels stage).
_MARKING_PREFIX = "marking."


def _absolute(placement: SymbolPlacement, local_x: float, local_y: float) -> tuple[int, int]:
    """A local, already-oriented module-unit port position as absolute page grid units."""
    return placement.x + to_grid(local_x), placement.y + to_grid(local_y)


@digest_cached(DIGEST_CACHE_SIZE)
def _page_ends(model: Model) -> dict[Id[Page], _Ends]:
    """Per page: every route endpoint (either end, D8) and every link marker's own `(x, y)`."""
    out: dict[Id[Page], _Ends] = {}
    for page in layout_of(model, PageRecord).values():
        ends = frozenset(
            (route.points[end].x, route.points[end].y)
            for route in page_slice(model, Route, page)
            for end in (0, -1)
        )
        out[page.id] = ends, frozenset((m.x, m.y) for m in page_slice(model, LinkMarker, page))
    return out


def _ends_of(model: Model, page: Page) -> _Ends:
    return _page_ends(model).get(page.id, _NO_ENDS)


def _route_ends(model: Model, page: Page) -> frozenset[_Grid]:
    """Every route endpoint on `page`, in grid units (either end, D8)."""
    return _ends_of(model, page)[0]


@digest_cached(DIGEST_CACHE_SIZE)
def _page_marked(model: Model) -> dict[tuple[Id[Page], Id[Function]], frozenset[str]]:
    """Per `(page, function)`: its local symbol ports with a marking label (render-0002)."""
    by_id = ports(model)
    found: dict[tuple[Id[Page], Id[Function]], set[str]] = {}
    for page in layout_of(model, PageRecord).values():
        for label in page_slice(model, Label, page):
            marking = label.kind is LabelKind.MARKING and label.slot.startswith(_MARKING_PREFIX)
            if marking and label.port is not None:
                key = (page.id, by_id[label.port].function)
                found.setdefault(key, set()).add(label.slot.removeprefix(_MARKING_PREFIX))
    return {key: frozenset(local) for key, local in found.items()}


def wired_local_ports(
    model: Model, page: Page, placement: SymbolPlacement, symbol: Symbol
) -> frozenset[str]:
    """`symbol`'s local port ids that have something on them on `page` (TL3)."""
    ends = _route_ends(model, page)
    markers = _ends_of(model, page)[1]
    marked = _page_marked(model).get((page.id, placement.function), frozenset())
    return frozenset(
        port.id
        for port in symbol.ports
        if port.id in marked
        or _absolute(placement, port.position.x, port.position.y) in ends
        or _absolute(placement, port.position.x, port.position.y) in markers
    )


def visible_symbol(model: Model, page: Page, placement: SymbolPlacement, symbol: Symbol) -> Symbol:
    """`symbol` with a bound lead left out unless its port is wired (TL3)."""
    wired = wired_local_ports(model, page, placement, symbol)

    def _dropped(element: object) -> bool:
        return isinstance(element, Line) and element.port is not None and element.port not in wired

    elements = tuple(element for element in symbol.elements if not _dropped(element))
    return replace(symbol, elements=elements)
