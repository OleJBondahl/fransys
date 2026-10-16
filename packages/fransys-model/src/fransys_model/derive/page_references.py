"""What a page's references say about their targets: spare contacts, other documents."""

from collections import Counter
from typing import Any
lazy from collections.abc import Mapping

from fransys_model.derive.contact_image import CONTACT_SLOTS, image_entries
from fransys_model.derive.frame_position import location_path, location_prefix
from fransys_model.derive.printed_sets import document_drawing_sets
from fransys_model.derive.rows_readability import OffDocumentReference
from fransys_model.layout import DrawingSet, Label, LabelKind, LinkMarker, Page, layout_of
from fransys_model.vocab.tables import documents
lazy from fransys_model.kernel import Id, Model

__all__ = ["contacts_not_drawn", "references_off_document"]


def contacts_not_drawn(model: Model) -> Counter[Id[Page]]:
    """The contact-image entries that print N/A, by the page of the coil's image.

    An entry is a spare contact when it names no partner port (`image_entries`).
    """
    return Counter(
        label.page
        for label in layout_of(model, Label).values()
        if label.kind is LabelKind.CROSS_REFERENCE and label.slot in CONTACT_SLOTS
        for column in image_entries(model, label)
        for _, port in column
        if port is None
    )


def _documents_of_sets(model: Model) -> dict[Id[DrawingSet], set[Id[Any]]]:
    """The documents that print each drawing set; a set no document prints has none."""
    found: dict[Id[DrawingSet], set[Id[Any]]] = {s: set() for s in layout_of(model, DrawingSet)}
    for doc_id, record in documents(model).items():
        for printed in document_drawing_sets(model, record.id):
            found[printed.id].add(doc_id)
    return found


def _off_document(
    model: Model, own: Page, target: Page, printed: Mapping[Id[DrawingSet], set[Id[Any]]]
) -> bool:
    """Whether `target` is off the document that prints `own`, and the text names no location."""
    if own.drawing_set == target.drawing_set or not printed[own.drawing_set]:
        return False
    if printed[own.drawing_set] & printed[target.drawing_set]:
        return False
    sets = layout_of(model, DrawingSet)
    here, there = (location_path(model, sets[p.drawing_set].location) for p in (own, target))
    return not location_prefix(here, there)


def references_off_document(model: Model) -> tuple[OffDocumentReference, ...]:
    """The printed references whose target is off the document and whose text names no other.

    A reference is a cross-reference label with partners, or a link marker with its partner. It
    is off the document when no document prints both its page's drawing set and its target's.
    Its text names the other document when it prints a location path (`location_prefix`).
    """
    pages, markers = layout_of(model, Page), layout_of(model, LinkMarker)
    printed = _documents_of_sets(model)
    ends: list[tuple[Id[Any], Id[Page], Id[Page]]] = [
        (label.id, label.page, partner.page)
        for label in layout_of(model, Label).values()
        for partner in label.partners
    ]
    ends += [(one.id, one.page, markers[one.partner].page) for one in markers.values()]
    off: dict[Id[Any], OffDocumentReference] = {}
    for subject, page, target in sorted(ends):
        if subject not in off and _off_document(model, pages[page], pages[target], printed):
            off[subject] = OffDocumentReference(subject=subject, page=page, target=target)
    return tuple(off.values())
