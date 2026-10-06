"""The model's house sheet and profile as stage values.

Refs: foundations.md 2.9, stages.md 6.1, engine.md 7.

Used when a model authors no `layout.profile` or `layout.sheet_format`. It reads the model's
layout defaults, so it lives in `read/`, the one place that may import `fransys_model.layout`.
"""

from fransys_layout.stages import Profile, SheetFormat
from fransys_model.derive.drawing_text import content_extent
from fransys_model.layout import Profile as ModelProfile
from fransys_model.layout import default_profile, default_sheet_format

# The model's house sheet (decision model-0029), in grid units: floor(mm / (module / 8)), so
# A3 landscape's content box of 410 x 267 mm at module 2.5 mm is 1312 x 854 (267 mm, not 277 or
# 287, since render spec D9 asked for a title-block band: decision model-0033, halved to 5 mm
# margins by page-frame spec R11.1, decision model-0051). One copy of the numbers: a `Page`
# with no sheet format is drawn on this.
_HOUSE_SHEET = default_sheet_format()
DEFAULT_SHEET = SheetFormat(
    name=_HOUSE_SHEET.name,
    content_width=content_extent(_HOUSE_SHEET.content_width_mm, _HOUSE_SHEET.module_mm),
    content_height=content_extent(_HOUSE_SHEET.content_height_mm, _HOUSE_SHEET.module_mm),
    frame_columns=_HOUSE_SHEET.frame_columns,
    frame_rows=_HOUSE_SHEET.frame_rows,
)


def to_stage_profile(profile: ModelProfile) -> Profile:
    """The stage `Profile` for a model `layout.profile` record, authored or the house default."""
    return Profile(
        column_gap=profile.column_gap,
        row_gap=profile.row_gap,
        row_spacing=profile.row_spacing,
        text_height=profile.text_height,
        marker_padding=profile.marker_padding,
        band_ranks=profile.band_ranks,
        group_ranks=profile.group_ranks,
        route_turn_penalty=profile.route_turn_penalty,
        route_crossing_penalty=profile.route_crossing_penalty,
        route_margin=profile.route_margin,
        hide_unused_pins=profile.hide_unused_pins,
    )


# The model's house profile (decision model-0036): one copy of the numbers, in
# `fransys_model.layout.default_profile()`, converted through `to_stage_profile` the
# same way an authored `layout.profile` would be.
DEFAULT_PROFILE = to_stage_profile(default_profile())
