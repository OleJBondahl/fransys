"""R428: a jog nest's bend row skips the rows the page already holds."""

from fransys_layout.core.jog_rows import bend_rows, taken_rows


def test_a_level_beside_a_taken_run_picks_the_next_free_row() -> None:
    taken = [(572, 500, 700)]  # y0 564 + one grid step of 8 is the first row
    assert bend_rows(564, 8, 4, [[(660, 676)]], []) == [0]
    assert bend_rows(564, 8, 4, [[(660, 676)]], taken) == [1]


def test_a_run_elsewhere_in_x_or_y_does_not_move_the_row() -> None:
    assert bend_rows(564, 8, 4, [[(660, 676)]], [(572, 800, 900), (580, 600, 700)]) == [0]


def test_a_wire_end_on_the_row_is_taken_and_the_levels_keep_their_order() -> None:
    taken = [(572, 668, 668)]
    assert bend_rows(564, 8, 4, [[(660, 676)], [(600, 640)]], taken) == [1, 2]


def test_no_free_row_in_the_room_keeps_the_depth_row() -> None:
    taken = [(572, 0, 999), (580, 0, 999)]
    assert bend_rows(564, 8, 2, [[(660, 676)]], taken) == [0]


def test_only_horizontal_segments_are_taken_runs() -> None:
    assert taken_rows([((0, 8), (40, 8)), ((4, 0), (4, 20)), ((6, 6), (6, 6))]) == ((8, 0, 40),)
