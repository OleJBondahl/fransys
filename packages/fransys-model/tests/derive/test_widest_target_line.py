"""`widest_target_line`: the longest line a reference marker can print (R350)."""

from derive_helpers import frozen_with_library

from fransys_model.derive import widest_position_text, widest_target_line
from fransys_model.kernel import Draft

MODEL = frozen_with_library(Draft())


def test_one_digit_numbers_in_an_8_by_6_frame() -> None:
    assert widest_target_line(MODEL, 1, 8, 6, "9") == "#9-p9:9F +9"


def test_each_extra_digit_of_the_page_or_the_frame_widens_the_line() -> None:
    assert widest_target_line(MODEL, 10, 12, 8, "9") == "#99-p99:99H +9"


def test_the_line_is_the_plus_form_so_no_printed_line_is_longer() -> None:
    from fransys_model.derive.marker_targets import target_lines

    two = target_lines(9, ["p9:9F", "p9:8F"])
    assert all(len(line) <= len(widest_target_line(MODEL, 1, 8, 6, "9")) for line in two)


def test_the_widest_position_text_counts_the_digits_of_the_symbol_count() -> None:
    """With no document there is no front page and no far-document prefix: the text is the page and the cell."""
    assert widest_position_text(MODEL, 1, 8, 6, "9") == "p9:9F"
    assert widest_position_text(MODEL, 10, 12, 8, "9") == "p99:99H"
