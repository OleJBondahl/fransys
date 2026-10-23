"""The warnings about the paper and the text size (R258; layout-0032 and layout-0179, moved here).

`SHEET_FORMAT_UNUSED` names each authored sheet format no profile and no paper choice uses;
`TEXT_TOO_SMALL` names each profile whose text height is under its floor. Neither changes a drawing.
"""

from typing import TYPE_CHECKING

from fransys_layout import FINDING_CODES
from fransys_model.derive import text_under_floor
from fransys_model.kernel import Finding, Severity
from fransys_model.layout import PaperChoice, Profile, SheetFormat, layout_of, sheet_format_of

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model

__all__ = ["text_floor_findings", "unused_sheet_findings"]

_INFO = {info.code: info for info in FINDING_CODES}


def _unused(model: Model) -> tuple[Id[SheetFormat], ...]:
    """The id of every authored sheet format no profile and no `PaperChoice` names."""
    used = {one.sheet_format for one in layout_of(model, Profile).values()}
    for paper in layout_of(model, PaperChoice).values():
        used |= {paper.default, *paper.by_kind.values()}
    return tuple(handle for handle in layout_of(model, SheetFormat) if handle not in used)


def unused_sheet_findings(model: Model) -> tuple[Finding, ...]:
    """One `SHEET_FORMAT_UNUSED` per authored sheet format nothing names (layout-0032)."""
    unused = _unused(model)
    if not unused:
        return ()
    top = next((p for p in layout_of(model, Profile).values() if p.unit is None), None)
    named = top.sheet_format if top is not None else None
    sheet = sheet_format_of(model, named)
    used = (
        f"the house sheet '{sheet.name}'"
        if named is None
        else f"the sheet format '{sheet.name}' that the layout profile names"
    )
    return tuple(
        Finding(
            code="SHEET_FORMAT_UNUSED",
            severity=Severity.WARNING,
            subjects=(handle,),
            message=f"no layout profile names this sheet format, so pages are drawn on {used}",
            fix=_INFO["SHEET_FORMAT_UNUSED"].filled(),
        )
        for handle in unused
    )


def text_floor_findings(model: Model) -> tuple[Finding, ...]:
    """One `TEXT_TOO_SMALL` per profile whose text height is under its minimum (layout-0179).

    The subject is the profile; a unit's own profile adds the unit.
    """
    found = []
    for profile in layout_of(model, Profile).values():
        printed = text_under_floor(profile)
        if printed is None:
            continue
        subjects = (profile.id,) if profile.unit is None else (profile.id, profile.unit)
        found.append(
            Finding(
                code="TEXT_TOO_SMALL",
                severity=Severity.WARNING,
                subjects=subjects,
                message=(
                    f"profile {'.'.join(profile.key)} sets a text height of "
                    f"{format(printed.normalize(), 'f')} mm, under its minimum of "
                    f"{format(profile.min_text_height_mm.normalize(), 'f')} mm"
                ),
                fix=_INFO["TEXT_TOO_SMALL"].filled(),
            )
        )
    return tuple(found)
