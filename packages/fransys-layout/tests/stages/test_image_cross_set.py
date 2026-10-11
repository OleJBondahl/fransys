"""A contact image names and measures a place in another drawing set as render prints it."""

from dataclasses import replace

from samples import PROFILE, SHEET, hid, page_plan

from fransys_layout.geometry import text_width
from fransys_layout.stages._image_widest import cross_form, widest_where
from fransys_model.derive.drawing_text import frame_column, frame_row

_FLD = ((hid("aspect_node", 7), "FLD"),)
_PATHS = {1: (), 2: _FLD}


def _cell(x: int, y: int) -> str:
    column = frame_column(SHEET.content_width, SHEET.frame_columns, x)
    return f"{column}{frame_row(SHEET.content_height, SHEET.frame_rows, y)}"


def test_the_widest_text_of_two_sets_is_the_longest_cross_set_text() -> None:
    """With two sets the reserve covers the prefix text; with one set it is unchanged."""
    # UNDO: stages/_image_widest.py `cross_form`: `return None` for every number of sets
    plans = (page_plan(("a",)), replace(page_plan(("b",)), drawing_set=2))
    cross = cross_form(plans, _PATHS)
    assert cross == (2, _FLD)
    alone = widest_where(1, SHEET, PROFILE)
    both = widest_where(1, SHEET, PROFILE, cross)
    assert text_width(both, height=PROFILE.text_height) > text_width(
        alone, height=PROFILE.text_height
    )
    assert both.startswith("+FLDp1:")
    assert cross_form(plans[:1], _PATHS) is None
