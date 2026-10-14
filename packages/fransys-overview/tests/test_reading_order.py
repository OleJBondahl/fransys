"""The reading order of a view's boxes: rows top down, each row left to right."""

from types import SimpleNamespace

from fransys_overview._data_order import reading_order


def _box(x: int, y: int, height: int = 10) -> SimpleNamespace:
    return SimpleNamespace(x=x, y=y, height=height)


def test_rows_read_top_down_and_each_row_left_to_right() -> None:
    boxes = [_box(50, 40), _box(10, 0), _box(30, 2), _box(0, 40)]
    assert reading_order(boxes) == [1, 2, 3, 0]


def test_a_box_a_little_lower_stays_in_its_row() -> None:
    boxes = [_box(20, 0, 20), _box(0, 5, 10)]
    assert reading_order(boxes) == [1, 0]


def test_every_index_once() -> None:
    boxes = [_box(i * 3 % 7, i * 5 % 11) for i in range(12)]
    assert sorted(reading_order(boxes)) == list(range(12))


def test_a_box_under_another_reads_after_it_before_the_next_column() -> None:
    """Breaks if a box lower than the row's least bottom starts a row of its own."""
    boxes = [_box(0, 0, 20), _box(10, 5, 10), _box(10, 12, 10), _box(20, 6, 10), _box(0, 40, 10)]
    assert reading_order(boxes) == [0, 1, 2, 3, 4]
