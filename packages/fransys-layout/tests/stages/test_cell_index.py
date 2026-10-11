"""`stages.cell_index.CellIndex`: items keyed by the wiring-grid cells their closed boxes meet.

The wiring grid is 8: a coordinate `c` is in cell `c // 8`, so x 0..7 is one cell and 8 the next.
"""

import random

from fransys_layout.geometry import Box
from fransys_layout.stages.cell_index import CellIndex


def _box(x: int, y: int, width: int = 0, height: int = 0) -> Box:
    return Box(x=x, y=y, width=width, height=height)


def test_negative_coordinates_floor_into_the_cells_below_zero() -> None:
    """UNDO: a cell is `int(c / 8)`, which truncates toward zero, and -1 lands in cell 0."""
    index = CellIndex([(_box(-1, 0), "left"), (_box(1, 0), "right")])
    assert index.meeting(-8, 0, -1, 0) == ("left",)
    assert index.meeting(0, 0, 7, 0) == ("right",)


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
