"""`reading_ranks`: a key's rank is its place top-down, left to right; a tie keeps arrival."""

from fransys_model.derive.order import by_place, reading_ranks


def test_ranks_follow_y_then_x_and_ties_keep_arrival() -> None:
    points = {"c": (2, 1), "a": (1, 5), "b": (1, 9), "d": (2, 1), "e": (0, 7)}
    assert reading_ranks(points) == {"e": 0, "a": 1, "b": 2, "c": 3, "d": 4}


def test_ranks_agree_with_by_place() -> None:
    class At:
        def __init__(self, name: str, x: int, y: int) -> None:
            self.name, self.x, self.y = name, x, y

    spots = [At("p", 4, 2), At("q", 1, 2), At("r", 9, 0), At("s", 1, 2)]
    ranks = reading_ranks({s.name: (s.y, s.x) for s in spots})
    assert sorted(ranks, key=ranks.__getitem__) == [s.name for s in by_place(spots)]
