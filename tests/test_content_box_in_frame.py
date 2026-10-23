"""The content box of every sheet preset lies inside the frame's border (DRAWING-INVARIANTS, R367).

OUT_OF_PAGE measures the content box; if it ever left the margin frame, the page frame's rule would
need the intersection of the two. This test keeps that from happening unseen.
"""

import tomllib
from decimal import Decimal
from importlib.resources import files

import pytest

from fransys_model.derive import sheet_frame
from fransys_model.kernel import make_id
from fransys_model.layout import SheetFormat, frame_form

PRESETS = tomllib.loads(files("fransys").joinpath("settings.toml").read_text())["paper"]["formats"]


_FORM = frame_form(row_labels="letters", column_labels="numbers", row_order="top_down")


def _sheet(name: str, table: dict) -> SheetFormat:
    fields = {k: table[k] for k in SheetFormat.__dataclass_fields__ if k in table}
    key = ("test", "paper", name)
    return SheetFormat(id=make_id(SheetFormat, key), key=key, module_mm=Decimal("2.5"), **fields)


@pytest.mark.parametrize("name", PRESETS)
def test_the_content_box_lies_inside_the_margin_frame(name: str) -> None:
    sheet = _sheet(name, PRESETS[name])
    x, y, w, h = sheet_frame(_FORM, sheet).border
    assert x <= sheet.content_x_mm
    assert y <= sheet.content_y_mm
    assert sheet.content_x_mm + sheet.content_width_mm <= x + w
    assert sheet.content_y_mm + sheet.content_height_mm <= y + h


def test_the_check_can_fail() -> None:
    wide = _sheet("A3", {**PRESETS["A3"], "content_width_mm": 412})
    x, _, w, _ = sheet_frame(_FORM, wide).border
    assert wide.content_x_mm + wide.content_width_mm > x + w
