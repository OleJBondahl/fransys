"""The connector-box rules: hand-made values, no model and no engine."""

from fransys_layout.geometry import WIRING_GRID
from fransys_layout.stages.connector_boxes import box_size, has_cells

G = WIRING_GRID  # 8
TH = 8  # text height; text_width("-W1-P1") = 26, ("DEMO-HSG-4M") = 57, ("A1") = 10 at it


def test_a_unit_interface_box_has_no_cells() -> None:
    """The black box test: an interface drawn as a black box has none, wired or not."""
    assert not has_cells(plug=False, black_box=True, board=False, wired=True)


def test_a_box_with_three_cells_is_as_wide_as_them_side_by_side() -> None:
    # cells: "1" 4+8 = 12 -> 16 (at least two grids), "12" 8+8 -> 16, "A1" 10+8 = 18
    # width: text 26+8 = 34 < cells 16+16+18 = 50, up to 56
    # height: one line 8 + padding 8 = 16, plus a cell row of two grids 16 = 32
    assert box_size(["-W1-P1"], ["1", "12", "A1"], text_height=TH) == (56, 32)
