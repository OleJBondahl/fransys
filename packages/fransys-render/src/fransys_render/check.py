"""Render-time checks, reported as findings (spec section 6, D12)."""

from typing import TYPE_CHECKING

from electrical_symbols import library_version
from fransys_model.derive import schematic_functions
from fransys_model.kernel import Finding, Severity
from fransys_model.layout import Page, SymbolPlacement, layout_of

from ._symbol_geometry import oriented_symbol

if TYPE_CHECKING:
    from fransys_model.kernel import Model

UNKNOWN_SYMBOL_KEY = "UNKNOWN_SYMBOL_KEY"
LIBRARY_VERSION_MISMATCH = "LIBRARY_VERSION_MISMATCH"
LAYOUT_MISSING = "LAYOUT_MISSING"


def _unknown_symbol_key_findings(
    model: Model, placements: tuple[SymbolPlacement, ...]
) -> tuple[Finding, ...]:
    """One `UNKNOWN_SYMBOL_KEY` (`ERROR`) per placement `oriented_symbol` cannot resolve."""
    return tuple(
        Finding(
            code=UNKNOWN_SYMBOL_KEY,
            severity=Severity.ERROR,
            subjects=(placement.function,),
            message=f"symbol {placement.symbol!r} is not in the library",
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
                f"installed is {installed!r}"
            ),
        )
        for placement in placements
        if oriented_symbol(model, placement) is not None
        if placement.library_version != installed
    )


def _layout_missing_findings(model: Model) -> tuple[Finding, ...]:
    """One `LAYOUT_MISSING` (`ERROR`) when schematic functions exist but no `layout.page` does."""
    if schematic_functions(model) and not layout_of(model, Page):
        return (
            Finding(
                code=LAYOUT_MISSING,
                severity=Severity.ERROR,
                subjects=(),
                message="the model has functions to draw but no layout.page record",
            ),
        )
    return ()


def check(model: Model) -> tuple[Finding, ...]:
    """Check what `pages` cannot draw or drew against a stale library (D12).

    Three checks: a placement's symbol key is not in the installed library
    (`UNKNOWN_SYMBOL_KEY`), a placement was laid out against a different library version
    than the one installed (`LIBRARY_VERSION_MISMATCH`, skipped for a placement already
    reported as unknown), and the model has schematic functions to draw but no laid-out
    page at all (`LAYOUT_MISSING`). Pure; raises nothing itself.

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
    )
    return tuple(sorted(findings, key=lambda finding: (finding.subjects, finding.code)))
