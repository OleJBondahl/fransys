"""`geometry.legs`: a polyline as legs, the merge modes and the ring (step 2, F2)."""

from fransys_layout.geometry import Point, legs


def _p(*xy: tuple[int, int]) -> list[Point]:
    return [Point(x=x, y=y) for x, y in xy]


def _ident(point: Point) -> Point:
    return point


def _coords(
    found: tuple[tuple[Point, Point], ...],
) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    return [((a.x, a.y), (b.x, b.y)) for a, b in found]


def test_same_joins_a_leg_going_on_and_not_a_fold_back() -> None:
    """`"same"` joins same-way legs; a fold-back stays two legs, `"any"` joins it."""
    onward = _p((0, 0), (0, 8), (0, 16))
    fold = _p((0, 0), (0, 16), (0, 8))
    assert _coords(legs(onward, at=_ident)) == [((0, 0), (0, 16))]
    assert _coords(legs(fold, at=_ident)) == [((0, 0), (0, 16)), ((0, 16), (0, 8))]
    assert _coords(legs(fold, at=_ident, merge="any")) == [((0, 0), (0, 8))]
