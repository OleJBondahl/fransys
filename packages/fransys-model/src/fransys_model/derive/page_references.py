"""What a page's references say about their targets: those that point into another document."""

from typing import Any
lazy from collections.abc import Mapping

from fransys_model.derive.designation import port_designation
from fransys_model.derive.page_reference_text import far_prefix, page_reference_text
from fransys_model.derive.printed_sets import document_drawing_sets
from fransys_model.derive.rows_readability import OffDocumentReference
from fransys_model.layout import DrawingSet, LinkMarker, Page, layout_of
from fransys_model.vocab.codes import finding
from fransys_model.vocab.tables import documents
lazy from fransys_model.kernel import Finding, Id, Model

__all__ = ["check_references_off_document", "references_off_document"]

REFERENCE_OFF_DOCUMENT = "REFERENCE_OFF_DOCUMENT"


def _documents_of_sets(model: Model) -> dict[Id[DrawingSet], set[Id[Any]]]:
    """The documents that print each drawing set; a set no document prints has none."""
    found: dict[Id[DrawingSet], set[Id[Any]]] = {s: set() for s in layout_of(model, DrawingSet)}
    for doc_id, record in documents(model).items():
        for printed in document_drawing_sets(model, record.id):
            found[printed.id].add(doc_id)
    return found


def _off_document(model: Model, own: Page, target: Page, printed: Mapping[Id[DrawingSet], set[Id[Any]]]) -> bool:
    """Whether `target` is off the document that prints `own`, and the text names no document."""
    if own.drawing_set == target.drawing_set or not printed[own.drawing_set]:
        return False
    if printed[own.drawing_set] & printed[target.drawing_set]:
        return False
    return not far_prefix(model, own, target)


def references_off_document(model: Model) -> tuple[OffDocumentReference, ...]:
    """The printed references whose target is off the document and whose text names no other.

    A reference is a link marker with its partner. It
    is off the document when no document prints both its page's drawing set and its target's.
    Its text names the other document by its `scope_path`, so it names none only when that is empty.
    """
    pages, markers = layout_of(model, Page), layout_of(model, LinkMarker)
    printed = _documents_of_sets(model)
    ends = [(one.id, one.page, markers[one.partner].page) for one in markers.values()]
    off: dict[Id[Any], OffDocumentReference] = {}
    for subject, page, target in ends:
        if subject not in off and _off_document(model, pages[page], pages[target], printed):
            off[subject] = OffDocumentReference(subject=subject, page=page, target=target)
    return tuple(off.values())


def check_references_off_document(model: Model) -> tuple[Finding, ...]:
    """One `REFERENCE_OFF_DOCUMENT` (`WARNING`) per reference to another, unnamed document, in `references_off_document` order."""
    pages, markers = layout_of(model, Page), layout_of(model, LinkMarker)
    return tuple(
        finding(
            REFERENCE_OFF_DOCUMENT,
            (one.subject,),
            f"the reference at {port_designation(model, markers[one.subject].port)} on "
            f"{page_reference_text(model, pages[one.page])} points to "
            f"{page_reference_text(model, pages[one.target])}, "
            "a page of another document, and its text does not name that document",
        )
        for one in references_off_document(model)
    )
