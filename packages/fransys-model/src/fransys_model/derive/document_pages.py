"""A document's drawn pages in order, and the drawing sets it prints.

A document's drawing sets are found by its location or unit. `fransys_pdf` paginates by them and
the overview links to them, so the one reading is here (the PDF's own page numbers cannot be
computed from the model, but each drawing page carries a named destination).
"""

from fransys_model.derive.facts.units import boundary
from fransys_model.layout import DrawingSet, LinkMarker, Page, layout_of
from fransys_model.layout.page_slices import page_members
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.document import Document

from .black_box import drawing_set_is_replica_only
from .document_sets import set_printers

__all__ = [
    "drawn_pages",
    "is_replica_only_undrawn",
    "ordered_pages",
    "page_order_key",
]


def is_replica_only_undrawn(model: Model, drawing_set: DrawingSet) -> bool:
    """Whether the set has drawn functions, all replicas, and no conductor row or `LinkMarker`.

    Read from the pages' `layout.membership` rows. A replica of the page unit's own boundary
    counts as drawn.
    """
    pages = [page for page in layout_of(model, Page).values() if page.drawing_set == drawing_set.id]
    rows = [row for page in pages for row in page_members(model, page)]
    placed = [row.function for row in rows if row.function is not None]
    if not placed:
        return False
    # pdf-0025: a replica of the page unit's own boundary (a pass-through) is its drawing
    if drawing_set.unit is not None and set(placed) & set(boundary(model, drawing_set.unit)):
        return False
    if not drawing_set_is_replica_only(model, drawing_set.id):
        return False
    has_conductor = any(row.conductor is not None for row in rows)
    ids = {page.id for page in pages}
    has_marker = any(marker.page in ids for marker in layout_of(model, LinkMarker).values())
    return not (has_conductor or has_marker)


def page_order_key(set_number: int, page: Page) -> tuple[int, int]:
    """The one page order: the page's drawing-set number, then its own number."""
    return (set_number, page.number)


def ordered_pages(model: Model, *, include_replica_only: bool = True) -> tuple[Page, ...]:
    """Every `layout.page` in set then page order; replica-only sets drop out when asked."""
    sets = layout_of(model, DrawingSet)
    skipped = set() if include_replica_only else {s.id for s in sets.values() if is_replica_only_undrawn(model, s)}
    pages = [p for p in layout_of(model, Page).values() if p.drawing_set not in skipped]
    return tuple(sorted(pages, key=lambda p: page_order_key(sets[p.drawing_set].number, p)))


def drawn_pages(model: Model, document: Id[Document]) -> tuple[Page, ...]:
    """The drawn pages of `document` in set then page order, replica-only sets skipped.

    `document` is the document's id.
    """
    printers = set_printers(model)
    sets = [s for s in layout_of(model, DrawingSet).values() if printers.get(s.id) == document and not is_replica_only_undrawn(model, s)]
    order = {s.id: s.number for s in sets}
    found = [p for p in layout_of(model, Page).values() if p.drawing_set in order]
    return tuple(sorted(found, key=lambda p: page_order_key(order[p.drawing_set], p)))
