"""Render-time checks, reported as findings."""

from typing import TYPE_CHECKING, Any

from fransys_model.derive import (
    function_is_loose,
    page_reference_text,
    port_designation,
    references_off_document,
    schematic_functions,
)
from fransys_model.kernel import Finding, Severity
from fransys_model.layout import LinkMarker, Page, layout_of

from .codes import fix_text

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model

LAYOUT_MISSING = "LAYOUT_MISSING"
BOARD_NETS_NOT_DRAWN = "BOARD_NETS_NOT_DRAWN"  # layout's code, read from the build's findings
REFERENCE_OFF_DOCUMENT = "REFERENCE_OFF_DOCUMENT"


def _boards_of(built: tuple[Finding, ...]) -> tuple[Id[Any], ...]:
    """The boards `built` reports as having nets that are not drawn, once each."""
    found = {s: None for one in built if one.code == BOARD_NETS_NOT_DRAWN for s in one.subjects}
    return tuple(found)


def _layout_missing_findings(model: Model, built: tuple[Finding, ...]) -> tuple[Finding, ...]:
    """One `LAYOUT_MISSING` (`ERROR`) when a schematic function to draw exists but no page does.

    A function with nothing connected is drawn on no page (`function_is_loose`, layout-0218). The
    subjects are the boards whose nets `built` reports as not drawn (layout-0322).
    """
    drawn = (f for f in schematic_functions(model) if not function_is_loose(model, f))
    if any(drawn) and not layout_of(model, Page):
        boards = _boards_of(built)
        note = f"; the nets of its subject boards are not drawn ({BOARD_NETS_NOT_DRAWN})"
        return (
            Finding(
                code=LAYOUT_MISSING,
                severity=Severity.ERROR,
                subjects=boards,
                fix=fix_text(LAYOUT_MISSING),
                message="the model has functions to draw but no layout.page record"
                + (note if boards else ""),
            ),
        )
    return ()


def _page_text(model: Model, page: Page) -> str:
    """`p3`, or `p2.3` for page 3 of set 2: the page as a reference prints it."""
    return page_reference_text(model, page)


def _reference_name(model: Model, subject: Id[Any]) -> str:
    """The designation a link marker reference stands at."""
    return port_designation(model, layout_of(model, LinkMarker)[subject].port)


def _reference_off_document_findings(model: Model) -> tuple[Finding, ...]:
    """One `REFERENCE_OFF_DOCUMENT` (`WARNING`) per reference to another, unnamed document."""
    pages = layout_of(model, Page)
    return tuple(
        Finding(
            code=REFERENCE_OFF_DOCUMENT,
            severity=Severity.WARNING,
            subjects=(one.subject,),
            fix=fix_text(REFERENCE_OFF_DOCUMENT),
            message=(
                f"the reference at {_reference_name(model, one.subject)} on "
                f"{_page_text(model, pages[one.page])} points to "
                f"{_page_text(model, pages[one.target])}, "
                "a page of another document, and its text does not name that document"
            ),
        )
        for one in references_off_document(model)
    )


def check(model: Model, built: tuple[Finding, ...] = ()) -> tuple[Finding, ...]:
    """Check what the core's pages cannot show: no page for connected functions, or a reference off.

    Two checks: functions to draw but no laid-out page (`LAYOUT_MISSING`, boards named from
    `built`) and a reference to another document that does not name it (`REFERENCE_OFF_DOCUMENT`,
    model-0258). Pure. Findings sorted by subject, then code.
    """
    findings = (*_layout_missing_findings(model, built), *_reference_off_document_findings(model))
    return tuple(sorted(findings, key=lambda finding: (finding.subjects, finding.code)))
