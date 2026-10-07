"""A reference's text, in every form `position_text` prints, fits its box (RR-O5 F11).

The box is one width per drawing set and sheet format (LD3 (c), S4). Derive prints the position
as a bare cell, `p<page>`, `p<set>.<page>` or behind `+<location>` labels; the box must hold the
longest of them at the set's digit counts.
"""

import pytest
from samples import PROFILE, SHEET

from fransys_layout.geometry import text_width
from fransys_layout.stages.references.digits import Digits
from fransys_layout.stages.references.marker_boxes import reference_box_width
from fransys_model.derive.drawing_text import frame_row, position_text

_COLUMN = SHEET.frame_columns
_LAST_ROW = frame_row(SHEET.content_height, SHEET.frame_rows, SHEET.content_height - 1)
_FORMS = {
    "same page": lambda: position_text(99, _COLUMN, _LAST_ROW, (), own_page=99),
    "same set": lambda: position_text(99, _COLUMN, _LAST_ROW, (), own_page=1),
    "other set": lambda: position_text(99, _COLUMN, _LAST_ROW, (), 99),
    "other location": lambda: position_text(99, _COLUMN, _LAST_ROW, ("C1", "C2"), 99),
}


# a run of two sets with `+C1+C2` between them, set numbers and sheets at two digits
_REACH = Digits(other_sets=2, prefix=("C1", "C2"))


@pytest.mark.parametrize("form", _FORMS)
def test_the_reference_box_holds_the_text_of_every_position_form(form: str) -> None:
    """`#99-<position>` at the two-digit floor is no wider than the box of a run of two sets."""
    # CAN-FAIL: references/marker_boxes.py `reference_texts`: drop the `other_sets` forms (the
    #     hand-built `#99-p99:<column><row>` only) and "other set" and "other location" fail
    text = f"#99-{_FORMS[form]()}"
    padding = 2 * PROFILE.marker_padding
    box = reference_box_width(SHEET, PROFILE, digits=_REACH)
    assert text_width(text, height=PROFILE.text_height) + padding <= box
