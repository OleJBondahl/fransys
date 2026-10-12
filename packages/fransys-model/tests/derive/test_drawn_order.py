"""`wire_run` and `by_place`: the drawn order reads a thing's own place, never its id."""

from typing import NamedTuple

from fransys_model.derive.order import NaturalKey, by_place, natural_key, wire_run


class _At(NamedTuple):
    x: int
    y: int
    name: str


def _local(one: _At) -> NaturalKey:
    return natural_key(one.name)


def test_a_wire_run_starts_at_its_upper_end() -> None:
    assert wire_run([(40, 40), (40, 42), (10, 42), (10, 40)]) == (
        (10, 40),
        (10, 42),
        (40, 42),
        (40, 40),
    )


def test_a_level_wire_run_starts_at_its_left_end() -> None:
    assert wire_run([(30, 5), (10, 5)]) == ((10, 5), (30, 5))


def test_a_wire_run_is_the_same_whichever_way_it_is_given() -> None:
    points = [(0, 0), (0, 8), (8, 8)]
    assert wire_run(points) == wire_run(points[::-1])


def test_by_place_runs_top_down_then_left_to_right_and_keeps_ties_in_order() -> None:
    drawn = [_At(5, 2, "late"), _At(1, 2, "left"), _At(9, 0, "top"), _At(5, 2, "same")]
    assert [one.name for one in by_place(drawn)] == ["top", "left", "late", "same"]


def test_by_place_breaks_a_full_geometry_tie_on_the_local_designation() -> None:
    drawn = [_At(5, 2, "-K10"), _At(5, 2, "-K2"), _At(1, 2, "-K9")]
    assert [one.name for one in by_place(drawn, _local)] == ["-K9", "-K2", "-K10"]


def test_by_place_keeps_input_order_when_the_designations_tie_too() -> None:
    first, second = _At(5, 2, "-K1"), _At(5, 2, "-K1")
    kept = by_place([first, second], _local)
    assert kept[0] is first
    assert by_place([second, first], _local)[0] is second


def test_geometry_decides_before_the_local_designation() -> None:
    drawn = [_At(9, 3, "-A"), _At(1, 4, "-A"), _At(2, 3, "-Z")]
    assert [(one.x, one.y) for one in by_place(drawn, _local)] == [(2, 3), (9, 3), (1, 4)]
