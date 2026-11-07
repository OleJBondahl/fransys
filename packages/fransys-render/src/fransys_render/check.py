"""Render-time checks, reported as findings."""

from typing import TYPE_CHECKING, Any

from fransys_model.derive import (
    page_reference_text,
    port_designation,
    references_off_document,
)
from fransys_model.layout import LinkMarker, Page, layout_of
lazy from fransys_model.kernel import Finding

from .codes import finding

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model

REFERENCE_OFF_DOCUMENT = "REFERENCE_OFF_DOCUMENT"


def _page_text(model: Model, page: Page) -> str:
    """`p3`: the page as a destination prints it."""
    return page_reference_text(model, page)


def _reference_name(model: Model, subject: Id[Any]) -> str:
    """The designation a link marker reference stands at."""
    return port_designation(model, layout_of(model, LinkMarker)[subject].port)


def _reference_off_document_findings(model: Model) -> tuple[Finding, ...]:
    """One `REFERENCE_OFF_DOCUMENT` (`WARNING`) per reference to another, unnamed document."""
    pages = layout_of(model, Page)
    return tuple(
        finding(
            REFERENCE_OFF_DOCUMENT,
            (one.subject,),
            f"the reference at {_reference_name(model, one.subject)} on "
            f"{_page_text(model, pages[one.page])} points to "
            f"{_page_text(model, pages[one.target])}, "
            "a page of another document, and its text does not name that document",
        )
        for one in references_off_document(model)
    )


def check(model: Model) -> tuple[Finding, ...]:
    """Check what the core's pages cannot show: a reference off its document.

    One check, `REFERENCE_OFF_DOCUMENT` (model-0258). Pure. Findings follow `references_off_document` (by subject).
    """
    return _reference_off_document_findings(model)
