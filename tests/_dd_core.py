"""Read the core path's drawn page for the dd_* tests: where a named item is drawn (DEL-4 lane C1).

The page Drawings carry no model id, so a thing is found by the text it prints: the item's
designation (`fransys_model.derive.item_designation`) in a tag, a slot, a cell, a label or a marker.
"""

import re
from typing import TYPE_CHECKING
lazy from collections.abc import Iterator

from _drawn_pages import drawn_pages

from fransys_model.derive import item_designation
from fransys_model.layout import DrawingSet, Page, layout_of
from fransys_model.vocab.tables import items
lazy from fransys_layout.drawing import Drawing

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model

__all__ = ["designation_of", "marker_texts", "pages_of", "pages_with", "set_of", "strings"]


def designation_of(model: Model, name: str) -> str:
    """The printed designation of the one item whose key ends in `name`."""
    (item,) = (i for i in items(model).values() if i.key[-1] == name)
    return item_designation(model, item.id)


def strings(drawing: Drawing) -> Iterator[str]:
    """Every string the page prints: texts, slots, cells, outline and wire labels, marker texts."""
    yield from (t.text for t in drawing.texts)
    for symbol in drawing.symbols:
        yield from (value for _, value in symbol.slots)
        yield from (cell for row in symbol.texts for cell in row)
    for outline in drawing.outlines:
        if outline.label is not None:
            yield outline.label.text
    yield from (w.label.text for w in drawing.wires if w.label is not None)
    for marker in drawing.markers:
        yield from (value for _, value in marker.texts)


def _names(text: str, designation: str) -> bool:
    return re.search(rf"(^|[-+ ]){re.escape(designation)}($|[:\-\s])", text) is not None


def pages_with(model: Model, designation: str) -> dict[Id[Page], Drawing]:
    """The pages (id -> Drawing) that print `designation` as a whole designation."""
    return {
        page: drawing
        for page, drawing in drawn_pages(model).items()
        if any(_names(text, designation) for text in strings(drawing))
    }


def pages_of(model: Model, name: str) -> dict[Id[Page], Drawing]:
    """The pages that print the designation of the item whose key ends in `name`."""
    return pages_with(model, designation_of(model, name))


def set_of(model: Model, page: Id[Page]) -> DrawingSet:
    """The drawing set `page` belongs to."""
    return layout_of(model, DrawingSet)[layout_of(model, Page)[page].drawing_set]


def marker_texts(model: Model, page: Id[Page]) -> list[str]:
    """Every text of every marker on `page`, in drawn order."""
    return [value for marker in drawn_pages(model)[page].markers for _, value in marker.texts]
