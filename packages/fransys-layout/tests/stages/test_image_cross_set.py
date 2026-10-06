"""RW9: a contact image names and measures a place in another drawing set as render prints it."""

import re
from dataclasses import replace

from samples import PROFILE, SHEET, hid, page_plan, placed

from fransys_layout.geometry import text_width
from fransys_layout.stages._image_widest import cross_form, widest_where
from fransys_layout.stages.images import _where
from fransys_model.derive.drawing_text import frame_column, frame_row, partner_position_text

_FLD = ((hid("aspect_node", 7), "FLD"),)
_PATHS = {1: (), 2: _FLD}


def _cell(x: int, y: int) -> str:
    column = frame_column(SHEET.content_width, SHEET.frame_columns, x)
    return f"{column}{frame_row(SHEET.content_height, SHEET.frame_rows, y)}"


def test_where_in_the_readers_own_set_is_the_cell_alone() -> None:
    """Same set and page: the cell only (model-0136)."""
    # UNDO: stages/images.py `_where`: pass `paths` and sets as `position_text(..., ())` did
    assert _where(SHEET, _PATHS, placed(2, x=200, y=0), placed(1, x=0, y=0)) == _cell(200, 0)


def test_where_in_another_set_carries_the_location_prefix() -> None:
    """Another set with a location below the common ancestor: `+FLDp1:<cell>`."""
    target = replace(placed(2, x=200, y=0), drawing_set=2)
    assert _where(SHEET, _PATHS, target, placed(1, x=0, y=0)) == f"+FLDp1:{_cell(200, 0)}"


def test_where_in_another_set_without_a_prefix_carries_the_set_number() -> None:
    """Another set whose path is no longer than the reader's: `p2.1:<cell>` (C18)."""
    target = replace(placed(2, x=200, y=0), drawing_set=2)
    assert _where(SHEET, {1: (), 2: ()}, target, placed(1, x=0, y=0)) == f"p2.1:{_cell(200, 0)}"


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


def test_the_widest_text_is_one_partner_position_text_form() -> None:
    """RW9: the reserve is a text `partner_position_text` prints: its cell, nothing appended."""
    # UNDO: stages/_image_widest.py `widest_where`: build the text without `partner_position_text`
    both = widest_where(1, SHEET, PROFILE, (2, _FLD))
    found = re.match(r"\+FLDp1:(\d+)([A-Z]+)", both)
    assert found
    column, row = found.groups()
    assert both == partner_position_text((1, 0, ()), (2, 1, _FLD), int(column), row)
