"""The findings of reading the model's sheet formats (layout-0032): one per unused one."""

from typing import TYPE_CHECKING, Any

from fransys_layout.lint.codes import SHEET_FORMAT_UNUSED
from fransys_model.kernel import Finding, Severity

if TYPE_CHECKING:
    from fransys_layout.stages.types import SheetFormat
    from fransys_model.kernel import Id


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
