"""Which drawing pages show an item and the PDF each is in (OVERVIEW O21), and a document's sets.

A document's drawing sets are found by its location or unit. `fransys_pdf` paginates by them and
the overview links to them, so the one reading is here (the PDF's own page numbers cannot be
computed from the model, but each drawing page carries a named destination).
"""

from collections import defaultdict

from fransys_model.kernel import Id, value
from fransys_model.layout import DrawingSet, LinkMarker, Page, Route, SymbolPlacement, layout_of
from fransys_model.vocab.membership import boundary
from fransys_model.vocab.tables import documents, functions
lazy from fransys_model.kernel import Model
lazy from fransys_model.vocab.core import Item
lazy from fransys_model.vocab.document import Document

from .black_box import drawing_set_is_replica_only
from .drawing_text import cell, position_text
from .export_names import document_export_name
from .page_destination import page_destination, set_rank
from .printed_sets import document_drawing_sets

__all__ = ["ItemPage", "drawn_pages", "is_replica_only_undrawn", "item_pages"]


def is_replica_only_undrawn(model: Model, drawing_set: DrawingSet) -> bool:
    """Whether the set has placements, all replicas, and no conductor route or `LinkMarker`.

    A replica of the page unit's own boundary counts as drawn.
    """
    pages = {
        page.id for page in layout_of(model, Page).values() if page.drawing_set == drawing_set.id
    }
    placed = [
        placement.function
        for placement in layout_of(model, SymbolPlacement).values()
        if placement.page in pages
    ]
    if not placed:
        return False
    # pdf-0025: a replica of the page unit's own boundary (a pass-through) is its drawing
    if drawing_set.unit is not None and set(placed) & set(boundary(model, drawing_set.unit)):
        return False
    if not drawing_set_is_replica_only(model, drawing_set.id):
        return False
    has_conductor_route = any(
        route.conductor is not None
        for route in layout_of(model, Route).values()
        if route.page in pages
    )
    has_marker = any(marker.page in pages for marker in layout_of(model, LinkMarker).values())
    return not (has_conductor_route or has_marker)


@value
class ItemPage:
    """One drawing page that shows an item: the PDF, the page's destination and its text."""

    file: str
    destination: str
    text: str


def drawn_pages(model: Model, record: Document) -> tuple[Page, ...]:
    """`record`'s drawn pages in set then page order, replica-only sets skipped."""
    sets = document_drawing_sets(model, record)
    sets = [s for s in sets if not is_replica_only_undrawn(model, s)]
    order = {s.id: s.number for s in sets}
    found = [p for p in layout_of(model, Page).values() if p.drawing_set in order]
    return tuple(sorted(found, key=lambda p: (order[p.drawing_set], p.number)))


def item_pages(model: Model) -> dict[Id[Item], tuple[ItemPage, ...]]:
    """Every item with each drawing page of a whole-system write that draws one of its functions.

    The file is the one `write` names the document's PDF; the text is `position_text` of the
    page and the frame cell of the first placement on it. Empty when the model has no document.
    """
    found: dict[Id[Item], dict[tuple[str, str], ItemPage]] = defaultdict(dict)
    by_page = defaultdict(list)
    for placement in layout_of(model, SymbolPlacement).values():
        by_page[placement.page].append(placement)
    funcs = functions(model)
    for record in documents(model).values():
        name = document_export_name(model, None, record)
        for page in drawn_pages(model, record):
            destination = page_destination(model, page)
            for placement in sorted(by_page[page.id], key=lambda p: (p.y, p.x)):
                column, row = cell(model, page, placement.x, placement.y)
                text = position_text(page.number, column, row, (), set_number=set_rank(model, page))
                item = funcs[placement.function].item
                found[item].setdefault(
                    (name, destination), ItemPage(file=name, destination=destination, text=text)
                )
    return {item: tuple(pages.values()) for item, pages in found.items()}
