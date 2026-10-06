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


def test_a_repeated_point_gives_no_leg() -> None:
    """Consecutive equal points are dropped under every merge mode."""
    points = _p((0, 0), (0, 0), (0, 8), (0, 8))
    for merge in ("none", "same", "any"):
        assert _coords(legs(points, at=_ident, merge=merge)) == [((0, 0), (0, 8))]  # type: ignore[arg-type]  -- merge is a parametrized str; legs takes a Literal


def test_none_keeps_collinear_legs_apart() -> None:
    """`merge="none"` leaves two legs on one line as two."""
    found = legs(_p((0, 0), (0, 8), (0, 16)), at=_ident, merge="none")
    assert _coords(found) == [((0, 0), (0, 8)), ((0, 8), (0, 16))]


def test_same_joins_a_leg_going_on_and_not_a_fold_back() -> None:
    """`"same"` joins same-way legs; a fold-back stays two legs, `"any"` joins it."""
    onward = _p((0, 0), (0, 8), (0, 16))
    fold = _p((0, 0), (0, 16), (0, 8))
    assert _coords(legs(onward, at=_ident)) == [((0, 0), (0, 16))]
    assert _coords(legs(fold, at=_ident)) == [((0, 0), (0, 16)), ((0, 16), (0, 8))]
    assert _coords(legs(fold, at=_ident, merge="any")) == [((0, 0), (0, 8))]


def test_a_diagonal_never_merges_under_same() -> None:
    """Two legs with the same diagonal direction stay two legs."""
    found = legs(_p((0, 0), (8, 8), (16, 16)), at=_ident)
    assert len(found) == 2


def test_a_corner_never_merges() -> None:
    """Legs on different axes are not joined by any mode."""
    for merge in ("same", "any"):
        assert len(legs(_p((0, 0), (0, 8), (8, 8)), at=_ident, merge=merge)) == 2  # type: ignore[arg-type]  -- merge is a parametrized str; legs takes a Literal


def test_ring_joins_the_last_leg_onto_the_first() -> None:
    """A closed loop that starts mid-side has its last leg joined onto its first."""
    loop = _p((0, 8), (0, 4), (8, 4), (8, 12), (0, 12), (0, 8))
    assert len(legs(loop, at=_ident)) == 5
    found = legs(loop, at=_ident, ring=True)
    assert len(found) == 4
    assert _coords(found)[0] == ((0, 12), (0, 4))


def test_ring_with_one_leg_or_a_corner_start_changes_nothing() -> None:
    """A single leg, or a loop whose first and last legs turn, is returned as is."""
    assert len(legs(_p((0, 0), (0, 8)), at=_ident, ring=True)) == 1
    square = _p((0, 0), (8, 0), (8, 8), (0, 8), (0, 0))
    assert len(legs(square, at=_ident, ring=True)) == 4


def test_at_reads_the_position_and_the_legs_keep_the_items() -> None:
    """Legs of wrapped points are pairs of the wrappers."""
    items = [("a", Point(x=0, y=0)), ("b", Point(x=0, y=8)), ("c", Point(x=0, y=16))]
    found = legs(items, at=lambda item: item[1])
    assert found == ((items[0], items[2]),)
