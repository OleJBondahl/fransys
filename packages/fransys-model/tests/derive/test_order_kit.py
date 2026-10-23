"""`order_kit`: each ordering function orders as its old inline `sorted`, `min` or `max` did."""

from fransys_model.derive.order_kit import first_device, lower_function, pin_items_in_order
from fransys_model.kernel import Id


def test_pin_items_ascend() -> None:
    assert pin_items_in_order({"b": 1, "a": 2}) == [("a", 2), ("b", 1)]


def test_first_device_takes_the_lowest_rank_then_the_lowest_handle() -> None:
    a, b = Id(kind="item", value="a"), Id(kind="item", value="b")
    assert first_device([b, a], {a: 2, b: 1}) == b
    assert first_device([b, a], {a: 1, b: 1}) == a


def test_lower_function_is_the_higher_rank_and_the_first_on_a_tie() -> None:
    one, other = Id(kind="function", value="x"), Id(kind="function", value="y")
    assert lower_function(one, other, (0, 1), (1, 0)) == other
    assert lower_function(one, other, (1, 0), (0, 1)) == one
    assert lower_function(one, other, (1, 1), (1, 1)) == one
