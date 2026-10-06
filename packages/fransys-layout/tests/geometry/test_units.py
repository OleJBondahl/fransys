"""WP1: `geometry.units` (ROADMAP WP1, docs/design/geometry.md 5.1)."""

import dataclasses
import math

import pytest

from fransys_layout.geometry import (
    GeometryError,
    Point,
    on_wiring_grid,
    snap_up,
    to_grid,
)


def test_to_grid_converts_module_units_exactly() -> None:
    """One module is eight grid units; the drawing grid step 0.125 M is one."""
    assert to_grid(1.0) == 8
    assert to_grid(0.125) == 1
    assert to_grid(-3.25) == -26
    assert to_grid(0.0) == 0


def test_to_grid_rejects_an_off_grid_coordinate() -> None:
    """A coordinate that is not a multiple of 0.125 M raises; it is never rounded."""
    with pytest.raises(GeometryError):
        to_grid(0.1)


def test_snap_up_never_moves_down() -> None:
    """`snap_up` keeps a multiple and lifts anything else to the next one."""
    assert snap_up(16) == 16
    assert snap_up(17) == 24
    assert snap_up(-1) == 0
    assert snap_up(5, grid=4) == 8


def test_on_wiring_grid_needs_both_coordinates() -> None:
    """A point is on the wiring grid only when x and y both are."""
    assert on_wiring_grid(Point(x=16, y=-8))
    assert not on_wiring_grid(Point(x=16, y=-7))


def test_to_grid_returns_an_int_and_converts_negative_values() -> None:
    """The result is an `int`, not the `float` that went in, and negative values convert."""
    assert to_grid(4.0) == 32
    assert to_grid(-0.125) == -1
    assert type(to_grid(4.0)) is int


def test_to_grid_accepts_the_grid_step_and_rejects_the_next_float_up() -> None:
    """The nearest off-grid neighbour of a legal value raises; the legal value does not."""
    assert to_grid(0.125) == 1
    with pytest.raises(GeometryError):
        to_grid(0.126)
    with pytest.raises(GeometryError):
        to_grid(0.0625)
    with pytest.raises(GeometryError):
        to_grid(-0.1)


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_to_grid_rejects_non_finite_values(bad: float) -> None:
    """`nan` and the infinities are not coordinates."""
    with pytest.raises(GeometryError):
        to_grid(bad)


def test_snap_up_lifts_negative_off_grid_values_toward_zero() -> None:
    """Rounding up on a negative value moves toward zero, never away from it."""
    assert snap_up(0) == 0
    assert snap_up(-8) == -8
    assert snap_up(-9) == -8
    assert snap_up(-15) == -8
    assert snap_up(7) == 8
    assert snap_up(8) == 8


def test_on_wiring_grid_rejects_an_off_grid_x_and_accepts_negatives() -> None:
    """Either coordinate off the grid fails the point; negative multiples pass."""
    assert on_wiring_grid(Point(x=0, y=0))
    assert on_wiring_grid(Point(x=-16, y=-8))
    assert not on_wiring_grid(Point(x=1, y=16))
    assert not on_wiring_grid(Point(x=-9, y=-8))


def test_point_is_frozen() -> None:
    """A `Point` cannot be mutated. Its `int` fields are enforced by `ty`, not at runtime."""
    point = Point(x=8, y=-8)
    with pytest.raises(dataclasses.FrozenInstanceError):
        point.x = 1  # ty: ignore[invalid-assignment] -- assigning to a frozen field, testing the refusal named in the raises
