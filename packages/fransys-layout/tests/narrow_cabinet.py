"""The cabinet laid out on an authored sheet of a chosen content width (narrow-sheet tests)."""

from decimal import Decimal
from functools import cache

from layout_cabinet import build_cabinet

from fransys_layout.engines.schematic.engine import StageResults, stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.engines.schematic.read.house import DEFAULT_PROFILE
from fransys_model.kernel import Finding, Model, Origin, freeze, make_id
from fransys_model.layout import Profile, SheetFormat


@cache
def narrow_results(width_mm: int) -> tuple[StageResults, tuple[Finding, ...]]:
    """The stage results and findings of the cabinet on a sheet with `width_mm` of content."""
    model = narrow_model(width_mm)
    return stage_results(model, read_inputs(model))


@cache
def narrow_model(width_mm: int) -> Model:
    """The cabinet on a sheet with `width_mm` of content, frozen, not laid out.

    The house profile values on the authored sheet: only the sheet's width changes.
    """
    draft = build_cabinet()
    sheet = SheetFormat(
        id=make_id(SheetFormat, ("test", "sheet")),
        key=("test", "sheet"),
        name="narrow",
        width_mm=width_mm + 20,
        height_mm=297,
        content_x_mm=10,
        content_y_mm=10,
        content_width_mm=width_mm,
        content_height_mm=277,
        frame_columns=8,
        frame_rows=6,
        module_mm=Decimal("2.5"),
    )
    profile = Profile(
        id=make_id(Profile, ("test", "profile")),
        key=("test", "profile"),
        sheet_format=sheet.id,
        column_gap=DEFAULT_PROFILE.column_gap,
        row_gap=DEFAULT_PROFILE.row_gap,
        route_margin=DEFAULT_PROFILE.route_margin,
        text_height=DEFAULT_PROFILE.text_height,
        marker_padding=DEFAULT_PROFILE.marker_padding,
        route_turn_penalty=DEFAULT_PROFILE.route_turn_penalty,
        route_crossing_penalty=DEFAULT_PROFILE.route_crossing_penalty,
        band_ranks=DEFAULT_PROFILE.band_ranks,
        group_ranks=DEFAULT_PROFILE.group_ranks,
    )
    draft.extend((sheet, profile), origin=Origin(file=__file__, line=1, note="narrow sheet"))
    return freeze(draft)
