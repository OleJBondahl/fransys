"""R428: a jog nest's bend row skips the rows the page already holds and the bodies it would run through."""

import pytest

from fransys_layout.core.clearance import footprint_keeps
from fransys_layout.core.jog_rows import bend_rows, taken_rows
from fransys_layout.core.values import Box

NONE = frozenset[str]()
ROWS = [572, 580, 588, 596]  # y0 564 and a grid step of 8


def _rows(ys, spans, taken, keeps=()):
    return bend_rows(ys, spans, taken, keeps, grid=8)


def test_a_level_beside_a_taken_run_picks_the_next_free_row() -> None:
    taken = [(572, 500, 700)]  # y0 564 + one grid step of 8 is the first row
    assert _rows(ROWS, [[(660, 676, NONE)]], []) == [0]
    assert _rows(ROWS, [[(660, 676, NONE)]], taken) == [1]


def test_a_taken_run_off_the_grid_blocks_the_grid_row_it_shares_a_cell_with() -> None:
    """KI-416: 574 and 572 are one 8-unit cell, so a stair row at 572 is not free."""
    assert _rows(ROWS, [[(500, 596, NONE)]], [(574, 580, 676)]) == [1]


def test_a_run_elsewhere_in_x_or_y_does_not_move_the_row() -> None:
    assert _rows(ROWS, [[(660, 676, NONE)]], [(572, 800, 900), (580, 600, 700)]) == [0]


def test_a_wire_end_on_the_row_is_taken_and_the_levels_keep_their_order() -> None:
    taken = [(572, 668, 668)]
    assert _rows(ROWS, [[(660, 676, NONE)], [(600, 640, NONE)]], taken) == [1, 2]


def test_no_free_row_in_the_room_returns_none() -> None:
    taken = [(572, 0, 999), (580, 0, 999)]
    assert _rows(ROWS[:2], [[(660, 676, NONE)]], taken) == [None]


def test_only_horizontal_segments_are_taken_runs() -> None:
    assert taken_rows([((0, 8), (40, 8)), ((4, 0), (4, 20)), ((6, 6), (6, 6))]) == ((8, 0, 40),)


@pytest.mark.rule("ROUTING")
def test_a_bend_row_across_another_nets_footprint_is_refused_but_its_own_is_not() -> None:
    keeps = tuple(footprint_keeps((("", "K9"),), Box(650, 570, 40, 20)))  # rows 572, 580 and 588 run through it
    assert _rows(ROWS, [[(660, 676, NONE)]], [], keeps) == [3]
    assert _rows(ROWS, [[(660, 676, frozenset({"K9"}))]], [], keeps) == [0]
