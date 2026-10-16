"""The page grid: columns count from 1 and rows from A over the whole area."""

from __future__ import annotations

import pytest

from fransys_layout.core import Size
from fransys_layout.core.text_cells import cell_of

AREA = Size(800, 600)
GRID = (8, 6)


def test_the_four_corners_of_the_default_grid_are_named_column_then_row() -> None:
    corners = [(0, 0), (800, 0), (0, 600), (800, 600)]
    assert [cell_of(x, y, AREA, GRID) for x, y in corners] == ["1A", "8A", "1F", "8F"]


def test_a_point_on_a_border_between_cells_goes_to_the_higher_cell() -> None:
    assert cell_of(100, 0, AREA, GRID) == "2A"
    assert cell_of(99, 99, AREA, GRID) == "1A"
    assert cell_of(100, 100, AREA, GRID) == "2B"


def test_the_option_sets_the_names() -> None:
    assert cell_of(800, 600, AREA, (4, 2)) == "4B"
    assert cell_of(200, 300, AREA, (4, 2)) == "2B"
    assert cell_of(199, 299, AREA, (4, 2)) == "1A"


@pytest.mark.parametrize("point", [(-1, 0), (801, 0), (0, -1), (0, 601)])
def test_a_point_outside_the_area_raises(point: tuple[int, int]) -> None:
    with pytest.raises(ValueError, match="outside"):
        cell_of(*point, AREA, GRID)


def test_a_grid_with_more_rows_than_letters_raises() -> None:
    with pytest.raises(ValueError, match="cannot be named"):
        cell_of(0, 0, AREA, (4, 27))
