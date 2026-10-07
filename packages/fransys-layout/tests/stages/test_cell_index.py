"""`stages.cell_index.CellIndex`: items keyed by the wiring-grid cells their closed boxes meet.

The wiring grid is 8: a coordinate `c` is in cell `c // 8`, so x 0..7 is one cell and 8 the next.
"""

import random

from fransys_layout.geometry import Box
from fransys_layout.stages.cell_index import CellIndex


def _box(x: int, y: int, width: int = 0, height: int = 0) -> Box:
    return Box(x=x, y=y, width=width, height=height)


def test_an_entry_in_a_cell_of_the_range_is_found_and_a_far_one_is_not() -> None:
    """UNDO: `meeting` returns every item, and the far entry is found."""
    index = CellIndex([(_box(0, 0, 4, 4), "near"), (_box(800, 800, 4, 4), "far")])
    assert index.meeting(0, 0, 7, 7) == ("near",)


def test_a_range_over_several_cells_finds_each_entry_in_entry_order() -> None:
    """UNDO: `meeting` returns the items sorted by cell, not by entry order."""
    index = CellIndex([(_box(40, 0), "c"), (_box(0, 0), "a"), (_box(16, 0), "b")])
    assert index.meeting(0, 0, 48, 0) == ("c", "a", "b")


def test_a_box_over_several_cells_is_found_once() -> None:
    """UNDO: `meeting` returns one item per cell it is stored under."""
    index = CellIndex([(_box(0, 0, 40, 40), "wide")])
    assert index.meeting(0, 0, 40, 40) == ("wide",)


def test_the_corner_pair_may_come_in_either_order() -> None:
    """UNDO: `_cells` reads the corners as given, and a reversed pair finds nothing."""
    index = CellIndex([(_box(16, 16), "point")])
    assert index.meeting(24, 24, 8, 8) == ("point",)


def test_a_zero_size_box_is_a_point_in_its_cell() -> None:
    """The point (8, 8) is in cell (1, 1): a query over cell (0, 0) misses it, (1, 1) finds it."""
    index = CellIndex([(_box(8, 8), "port")])
    assert index.meeting(0, 0, 7, 7) == ()
    assert index.meeting(8, 8, 8, 8) == ("port",)


def test_a_box_edge_on_a_cell_boundary_is_stored_under_both_cells() -> None:
    """UNDO: the far edge is stored under `(x + width - 1) // 8`, and a touch at 8 is lost."""
    index = CellIndex([(_box(0, 0, 8, 8), "box")])
    assert index.meeting(8, 8, 8, 8) == ("box",)


def test_negative_coordinates_floor_into_the_cells_below_zero() -> None:
    """UNDO: a cell is `int(c / 8)`, which truncates toward zero, and -1 lands in cell 0."""
    index = CellIndex([(_box(-1, 0), "left"), (_box(1, 0), "right")])
    assert index.meeting(-8, 0, -1, 0) == ("left",)
    assert index.meeting(0, 0, 7, 0) == ("right",)


def test_an_empty_index_meets_nothing() -> None:
    assert CellIndex([]).meeting(0, 0, 100, 100) == ()


def _hit(box: Box, first: tuple[int, int], second: tuple[int, int]) -> bool:
    """Brute force: the closed box meets the closed axis-aligned segment."""
    low_x, high_x = sorted((first[0], second[0]))
    low_y, high_y = sorted((first[1], second[1]))
    return (
        box.x <= high_x
        and low_x <= box.x + box.width
        and box.y <= high_y
        and low_y <= box.y + box.height
    )


def test_every_box_that_meets_a_segment_is_among_the_candidates() -> None:
    """UNDO: a box is stored under its first cell only, and a box that meets by its far end is lost.

    Seeded: 300 boxes and 300 axis-aligned segments; the candidates hold every true hit.
    """
    rng = random.Random(133)  # noqa: S311 - a seeded test generator, not cryptography
    boxes = [
        _box(rng.randint(-100, 300), rng.randint(-100, 300), rng.randint(0, 60), rng.randint(0, 60))
        for _ in range(300)
    ]
    index = CellIndex((box, number) for number, box in enumerate(boxes))
    for _ in range(300):
        first = (rng.randint(-120, 320), rng.randint(-120, 320))
        second = (
            (first[0], rng.randint(-120, 320))
            if rng.random() < 0.5
            else (
                rng.randint(-120, 320),
                first[1],
            )
        )
        found = index.meeting(*first, *second)
        assert list(found) == sorted(set(found))
        assert {n for n, box in enumerate(boxes) if _hit(box, first, second)} <= set(found)
