"""`diagram_marker_text`: a cut marker prints its partner's place on the other sheet."""

from derive_helpers import frozen_with_library

from fransys_model.derive.block_diagram import diagram_marker_text
from fransys_model.kernel import Draft


def _text(sheet: int, at_sheet: int, cell: tuple[int, str]) -> str:
    return diagram_marker_text(frozen_with_library(Draft()), sheet, at_sheet, *cell)


def test_two_cut_lines_of_one_pair_of_sheets_name_their_own_partners() -> None:
    assert _text(1, 2, (1, "H")) == "p2:1H"


def test_the_partner_position_picks_the_cell_of_the_other_sheet() -> None:
    first, second = _text(1, 2, (1, "C")), _text(1, 2, (1, "H"))
    assert first != second
    assert first.startswith("p2:1")
    assert _text(2, 1, (11, "A")).startswith("p1:")
