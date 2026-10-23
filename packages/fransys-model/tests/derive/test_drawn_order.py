"""`by_place`: the drawn order reads a thing's place, not its id."""

from typing import NamedTuple

from fransys_model.derive.order import by_place


class _At(NamedTuple):
    x: int
    y: int
    name: str


def test_by_place_runs_top_down_then_left_to_right_and_keeps_ties_in_order() -> None:
    drawn = [_At(5, 2, "late"), _At(1, 2, "left"), _At(9, 0, "top"), _At(5, 2, "same")]
    assert [one.name for one in by_place(drawn)] == ["top", "left", "late", "same"]
