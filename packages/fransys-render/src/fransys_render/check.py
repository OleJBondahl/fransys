"""Render-time checks, reported as findings."""

from typing import TYPE_CHECKING, Any, cast

from electrical_symbols import library_version
from fransys_model.derive import (
    function_designation,
    function_is_loose,
    page_reference_text,
    port_designation,
    references_off_document,
    schematic_functions,
)
from fransys_model.kernel import Finding, SchemaError, Severity
from fransys_model.layout import Label, LinkMarker, Page, SymbolPlacement, layout_of

from ._drawn_shorts import drawn_shorts
from ._ink import page_ink
from ._symbol_geometry import oriented_symbol

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Function

UNKNOWN_SYMBOL_KEY = "UNKNOWN_SYMBOL_KEY"
LIBRARY_VERSION_MISMATCH = "LIBRARY_VERSION_MISMATCH"
LAYOUT_MISSING = "LAYOUT_MISSING"
DRAWING_SHORTS_NETS = "DRAWING_SHORTS_NETS"
REFERENCE_OFF_DOCUMENT = "REFERENCE_OFF_DOCUMENT"


def _about(model: Model, placement: SymbolPlacement) -> str:
    """` (p3: H1:lamp)`: the placement's page as a reference prints it, then its function."""
    page = layout_of(model, Page)[placement.page]
    where = page_reference_text(model, page, with_location=True)
    try:
        return f" ({where}: {function_designation(model, placement.function)})"
    except SchemaError:
        return f" ({where})"


def _unknown_symbol_key_findings(
    model: Model, placements: tuple[SymbolPlacement, ...]
) -> tuple[Finding, ...]:
    """One `UNKNOWN_SYMBOL_KEY` (`ERROR`) per placement `oriented_symbol` cannot resolve."""
    return tuple(
        Finding(
            code=UNKNOWN_SYMBOL_KEY,
            severity=Severity.ERROR,
            subjects=(placement.function,),
            message=f"symbol {placement.symbol!r} is not in the library{_about(model, placement)}",
        )
        for placement in placements
        if oriented_symbol(model, placement) is None
    )


def _library_version_mismatch_findings(
    model: Model, placements: tuple[SymbolPlacement, ...]
) -> tuple[Finding, ...]:
    """One `LIBRARY_VERSION_MISMATCH` (`WARNING`) per placement laid out with a stale version."""
    installed = library_version()
    return tuple(
        Finding(
            code=LIBRARY_VERSION_MISMATCH,
            severity=Severity.WARNING,
            subjects=(placement.function,),
            message=(
                f"placement laid out with library version {placement.library_version!r}, "
                f"installed is {installed!r}{_about(model, placement)}"
            ),
        )
        for placement in placements
        if oriented_symbol(model, placement) is not None
        if placement.library_version != installed
    )


def _layout_missing_findings(model: Model) -> tuple[Finding, ...]:
    """One `LAYOUT_MISSING` (`ERROR`) when a schematic function to draw exists but no page does.

    A function with nothing connected is drawn on no page (`function_is_loose`, layout-0218).
    """
    drawn = (f for f in schematic_functions(model) if not function_is_loose(model, f))
    if any(drawn) and not layout_of(model, Page):
        return (
            Finding(
                code=LAYOUT_MISSING,
                severity=Severity.ERROR,
                subjects=(),
                message="the model has functions to draw but no layout.page record",
            ),
        )
    return ()


def _drawing_shorts_nets_findings(model: Model) -> tuple[Finding, ...]:
    """One `DRAWING_SHORTS_NETS` per pair of nets a page draws joined (render-0012)."""
    return tuple(
        Finding(
            code=DRAWING_SHORTS_NETS,
            severity=Severity.INFO,  # ERROR once the drawn shorts it finds are fixed
            subjects=short.subjects,
            message="the drawing joins two nets: a stub, wire end or symbol lies on other ink",
        )
        for page in sorted(layout_of(model, Page).values(), key=lambda one: one.id)
        for short in drawn_shorts(*page_ink(model, page))
    )


def _page_text(model: Model, page: Page) -> str:
    """`p3`, or `p2.3` for page 3 of set 2: the page as a reference prints it."""
    return page_reference_text(model, page)


def _reference_name(model: Model, subject: Id[Any]) -> str:
    """The designation a label or link marker reference stands at."""
    label = layout_of(model, Label).get(subject)
    if label is None:
        return port_designation(model, layout_of(model, LinkMarker)[subject].port)
    return function_designation(model, cast("Id[Function]", label.function))


def _reference_off_document_findings(model: Model) -> tuple[Finding, ...]:
    """One `REFERENCE_OFF_DOCUMENT` (`WARNING`) per reference to another, unnamed document."""
    pages = layout_of(model, Page)
    return tuple(
        Finding(
            code=REFERENCE_OFF_DOCUMENT,
            severity=Severity.WARNING,
            subjects=(one.subject,),
            message=(
                f"the reference at {_reference_name(model, one.subject)} on "
                f"{_page_text(model, pages[one.page])} points to "
                f"{_page_text(model, pages[one.target])}, "
                "a page of another document, and its text does not name that document"
            ),
        )
        for one in references_off_document(model)
    )


def check(model: Model) -> tuple[Finding, ...]:
    """Check what `pages` cannot draw or drew against a stale library.

    Five checks: a symbol key not in the installed library (`UNKNOWN_SYMBOL_KEY`), a placement
    laid out against another library version (`LIBRARY_VERSION_MISMATCH`, skipped when already
    unknown), functions to draw but no laid-out page (`LAYOUT_MISSING`), a page drawing two nets
    joined (`DRAWING_SHORTS_NETS`), and a reference to another document that does not name it
    (`REFERENCE_OFF_DOCUMENT`, model-0258).
    Pure; raises nothing itself.

    Args:
        model: A laid-out model.

    Returns:
        Findings sorted by subject, then code.
    """
    placements = tuple(
        sorted(layout_of(model, SymbolPlacement).values(), key=lambda placement: placement.id)
    )
    findings = (
        *_unknown_symbol_key_findings(model, placements),
        *_library_version_mismatch_findings(model, placements),
        *_layout_missing_findings(model),
        *_drawing_shorts_nets_findings(model),
        *_reference_off_document_findings(model),
    )
    return tuple(sorted(findings, key=lambda finding: (finding.subjects, finding.code)))
