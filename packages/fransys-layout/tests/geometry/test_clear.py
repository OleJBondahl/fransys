"""`geometry.clear`: the first free candidate and a box pushed clear (cleanup step 2, F3)."""

from fransys_layout.geometry import Box, first_clear, overlaps, push_clear


def test_first_clear_takes_the_first_unblocked_candidate_lazily() -> None:
    """Candidates are tried in order and the rest is not evaluated."""
    seen: list[int] = []

    def candidates():
        for n in (1, 2, 3, 4):
            seen.append(n)
            yield n

    got = first_clear(
        candidates(), box_of=lambda n: Box(x=n, y=0, width=1, height=1), blocked=lambda b: b.x < 3
    )
    assert got == 3
    assert seen == [1, 2, 3]


def test_first_clear_gives_default_when_all_are_blocked() -> None:
    """With every candidate blocked the default comes back, `None` unless given."""
    box_of = lambda n: Box(x=n, y=0, width=1, height=1)  # noqa: E731 - a one-line test helper
    assert first_clear([1, 2], box_of=box_of, blocked=lambda _: True) is None
    assert first_clear([1, 2], box_of=box_of, blocked=lambda _: True, default=2) == 2


def test_push_clear_moves_down_to_a_fixed_point_with_the_gap() -> None:
    """A box on one blocker lands under it, and under the next one it then meets."""
    blockers = [Box(x=0, y=0, width=8, height=8), Box(x=0, y=10, width=8, height=8)]
    got = push_clear(Box(x=0, y=0, width=8, height=4), blockers, gap=2, axis="y")
    assert got == Box(x=0, y=20, width=8, height=4)
    assert not any(overlaps(got, b) for b in blockers)


def test_push_clear_leaves_a_clear_box_and_ignores_a_zero_size_blocker() -> None:
    """Nothing overlaps, nothing moves; an empty blocker never blocks."""
    box = Box(x=0, y=0, width=8, height=8)
    assert push_clear(box, [Box(x=0, y=8, width=8, height=8)], gap=4, axis="y") == box
    assert push_clear(box, [Box(x=2, y=2, width=0, height=0)], gap=4, axis="y") == box


def test_push_clear_on_x_moves_right() -> None:
    """On the x axis the box goes right, past the blocker's right edge plus the gap."""
    got = push_clear(
        Box(x=0, y=0, width=4, height=8), [Box(x=0, y=0, width=8, height=8)], gap=2, axis="x"
    )
    assert got == Box(x=10, y=0, width=4, height=8)
