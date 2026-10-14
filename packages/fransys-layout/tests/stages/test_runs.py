"""`member_runs` and `run_box`, the general run finding of the outlines (OUTLINES BO5).

Can-fail (each by one mutation of `stages/runs.py`):
- OUTLINE-ENCLOSE: `_cut_by_foreign(run, placed) if enclose else [run]` -> `[run]` (the foreign
  symbol between two members test).
- a foreign column between two member columns cuts: `others = [... if one.column not in own]`
  -> `others = []` (the foreign column test).
- the box's padding: `whole.x - padding` -> `whole.x` (the box test).
"""

from types import SimpleNamespace
from typing import Any, cast

from fransys_layout.geometry import Box
from fransys_layout.stages.runs import member_runs, run_box

_BODY = Box(x=0, y=0, width=4, height=8)


def _one(function: str, column: str, x: int, y: int) -> Any:
    """A placed function of one body 4 x 8 at (x, y)."""
    return SimpleNamespace(
        function=function,
        column=column,
        at=SimpleNamespace(x=x, y=y),
        geometry=SimpleNamespace(body=_BODY),
    )


def _names(runs: list[list[Any]]) -> list[list[str]]:
    return [[cast("str", one.function) for one in run] for run in runs]


def test_neighbouring_columns_are_one_run() -> None:
    a, b = _one("a", "ca", 20, 20), _one("b", "cb", 40, 20)
    assert _names(member_runs([a, b], [a, b])) == [["a", "b"]]


def test_a_foreign_column_between_two_member_columns_cuts_the_run() -> None:
    a, b, x = _one("a", "ca", 20, 20), _one("b", "cb", 60, 20), _one("x", "cx", 40, 20)
    assert _names(member_runs([a, b], [a, b, x])) == [["a"], ["b"]]


def test_a_foreign_symbol_between_two_members_of_a_column_cuts_the_run() -> None:
    a, b, x = _one("a", "ca", 20, 20), _one("b", "ca", 20, 60), _one("x", "ca", 20, 40)
    assert _names(member_runs([a, b], [a, b, x])) == [["a"], ["b"]]
    assert _names(member_runs([a, b], [a, b, x], enclose=False)) == [["a", "b"]]


def test_the_box_holds_bodies_and_texts_with_the_padding_and_stays_right_of_zero() -> None:
    a, b = _one("a", "ca", 20, 20), _one("b", "ca", 20, 40)
    text = Box(x=30, y=10, width=10, height=4)
    assert run_box([a, b], [text], padding=4) == Box(x=16, y=6, width=28, height=46)
    near = _one("n", "ca", 2, 20)
    assert run_box([near], padding=4).x == 0


def test_an_obstacle_box_inside_a_run_cuts_it_beside_the_obstacle() -> None:
    """OUTLINES BO6. Probe: `runs.extend(_cut_by_obstacles(part, obstacles))` to append."""
    a, b = _one("a", "ca", 20, 20), _one("b", "cb", 60, 20)
    wall = Box(x=36, y=22, width=8, height=4)
    assert _names(member_runs([a, b], [a, b], obstacles=[wall])) == [["a"], ["b"]]
    clear = Box(x=36, y=60, width=8, height=4)
    assert _names(member_runs([a, b], [a, b], obstacles=[clear])) == [["a", "b"]]
    above = [_one("c", "cc", 20, 20), _one("d", "cc", 20, 80)]
    mid = Box(x=18, y=48, width=8, height=4)
    assert _names(member_runs(above, above, enclose=False, obstacles=[mid])) == [["c"], ["d"]]
