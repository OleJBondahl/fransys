"""`widest_target_line`: the longest line a reference marker can print (R350)."""

from fransys_model.derive import widest_target_line


def test_one_digit_numbers_in_an_8_by_6_frame() -> None:
    assert widest_target_line(1, 8, 6, "9") == "#9-p9:9F +9"


def test_each_extra_digit_of_the_page_or_the_frame_widens_the_line() -> None:
    assert widest_target_line(2, 12, 8, "9") == "#99-p99:99H +9"


def test_the_line_is_the_plus_form_so_no_printed_line_is_longer() -> None:
    from fransys_model.derive.marker_targets import target_lines

    two = target_lines(9, ["p9:9F", "p9:8F"])
    assert all(len(line) <= len(widest_target_line(1, 8, 6, "9")) for line in two)
