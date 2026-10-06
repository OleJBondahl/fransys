"""`port_exit`: a port's wire leaves one wiring grid along its facing (route.md 6.5, rule table)."""

import pytest

from fransys_layout.geometry import FACING_STEP, WIRING_GRID, Facing, Point, port_exit


@pytest.mark.parametrize(
    ("facing", "grids", "expected"),
    [
        (Facing.N, 1, Point(x=40, y=24 - WIRING_GRID)),
        (Facing.S, 1, Point(x=40, y=24 + WIRING_GRID)),
        (Facing.E, 1, Point(x=40 + WIRING_GRID, y=24)),
        (Facing.W, 1, Point(x=40 - WIRING_GRID, y=24)),
        (Facing.W, 3, Point(x=40 - 3 * WIRING_GRID, y=24)),
    ],
)
def test_a_port_exit_stands_the_stated_grids_out_along_its_facing(
    facing: Facing, grids: int, expected: Point
) -> None:
    """Hand-made values for all four facings, and for three grids out."""
    assert port_exit(Point(x=40, y=24), facing, grids) == expected


def test_the_default_is_one_grid_and_the_step_table_covers_every_facing() -> None:
    """One grid without `grids`; `FACING_STEP` has the four facings, each one grid long."""
    assert port_exit(Point(x=0, y=0), Facing.E) == Point(x=WIRING_GRID, y=0)
    assert set(FACING_STEP) == set(Facing)
    assert all(abs(dx) + abs(dy) == WIRING_GRID for dx, dy in FACING_STEP.values())
