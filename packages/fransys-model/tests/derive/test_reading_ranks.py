"""`reading_ranks`: a key's rank is its place top-down, left to right; a tie keeps arrival."""

from fransys_model.derive.order import reading_ranks


def test_ranks_follow_y_then_x_and_ties_keep_arrival() -> None:
    points = {"c": (2, 1), "a": (1, 5), "b": (1, 9), "d": (2, 1), "e": (0, 7)}
    assert reading_ranks(points) == {"e": 0, "a": 1, "b": 2, "c": 3, "d": 4}


def test_in_place_order_is_top_down_left_to_right_and_a_tie_keeps_arrival() -> None:
    from fransys_model.derive.order import in_place_order

    found = [(5, 9, "c"), (1, 7, "b1"), (1, 2, "a"), (1, 7, "b2")]
    assert in_place_order(found) == ("a", "b1", "b2", "c")
