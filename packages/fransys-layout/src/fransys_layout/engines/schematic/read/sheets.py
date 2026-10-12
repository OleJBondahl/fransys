"""The findings of reading the model's sheet formats (layout-0032): one per unused one."""

from typing import TYPE_CHECKING, Any

from fransys_layout.lint.codes import SHEET_FORMAT_UNUSED, TEXT_TOO_SMALL
from fransys_model.derive import text_size_mm, text_under_floor
from fransys_model.kernel import Finding, Severity
from fransys_model.layout import profile_of, sheet_format_of

if TYPE_CHECKING:
    from decimal import Decimal

    from fransys_layout.stages.types import SheetFormat
    from fransys_model.kernel import Id, Model


def unused_sheet_findings(
    sheet: SheetFormat, sheet_format: Id[Any] | None, unused: tuple[Id[Any], ...]
) -> tuple[Finding, ...]:
    """One `SHEET_FORMAT_UNUSED` per authored sheet format no profile names (layout-0032)."""
    if sheet_format is None:
        used = f"the house sheet '{sheet.name}'"
    else:
        used = f"the sheet format '{sheet.name}' that the layout profile names"
    return tuple(
        Finding(
            code=SHEET_FORMAT_UNUSED,
            severity=Severity.WARNING,
            subjects=(handle,),
            message=f"no layout profile names this sheet format, so pages are drawn on {used}",
        )
        for handle in unused
    )


def printed_text(model: Model, unit: Id[Any] | None) -> tuple[Decimal, Decimal]:
    """The printed text size of `unit`'s profile in mm, and the `min_text_mm` it is held to."""
    profile = profile_of(model, unit)
    sheet = sheet_format_of(model, profile.sheet_format)
    return text_size_mm(profile.text_height, sheet.module_mm), profile.min_text_mm


def text_floor_findings(model: Model, unit: Id[Any] | None) -> tuple[Finding, ...]:
    """One `TEXT_TOO_SMALL` when `unit`'s profile prints text under its `min_text_mm` (layout-0179).

    The subject is the profile; a unit's own profile adds the unit, so the per-profile merge
    (model-0192) keeps the finding of the run that read it. It never changes a drawing.
    """
    profile = profile_of(model, unit)
    sheet = sheet_format_of(model, profile.sheet_format)
    printed = text_under_floor(profile, sheet.module_mm)
    if printed is None:
        return ()
    name = ".".join(profile.key)
    subjects = (profile.id,) if profile.unit is None else (profile.id, profile.unit)
    return (
        Finding(
            code=TEXT_TOO_SMALL,
            severity=Severity.WARNING,
            subjects=subjects,
            message=(
                f"profile {name} prints text at {format(printed.normalize(), 'f')} mm, "
                f"under its minimum of {format(profile.min_text_mm.normalize(), 'f')} mm"
            ),
        ),
    )
