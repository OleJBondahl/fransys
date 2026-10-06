"""`place`'s row-stacking adapters equal their pre-`flow` code on random rows (CLEANUP step 2)."""

import random
from types import SimpleNamespace
from typing import Any
lazy from collections.abc import Sequence

from fransys_layout.geometry import Box
from fransys_layout.stages.place import _cascade_plan, _Cell, _raise_plan, _stack

_CASES = 600


def _rng(seed: float) -> random.Random:
    return random.Random(seed)  # noqa: S311 -- seeded test data


def _cell(rng: random.Random) -> _Cell:
    keepout = Box(x=0, y=rng.choice([-7, -3, 0, 2, 5]), width=10, height=rng.randint(1, 40))
    geometry: Any = SimpleNamespace(keepout=keepout)
    cell = _Cell(function=None, column=None, geometry=geometry, band=None, axis_offset=0)  # ty: ignore[invalid-argument-type] -- stand-ins; only keepout is read
    cell.at_top(rng.randint(-20, 200))
    return cell


def _rows(rng: random.Random) -> list[list[_Cell]]:
    return [[_cell(rng) for _ in range(rng.randint(1, 3))] for _ in range(rng.randint(1, 7))]


def _old_raise_plan(
    rows: Sequence[list[_Cell]], start: int, top: int, gaps: Sequence[int]
) -> list[tuple[int, int]]:
    shift = min(cell.top for cell in rows[start]) - top
    moves = [(start, shift)]
    below = min(cell.top_at(cell.top - shift) for cell in rows[start])
    for index in range(start - 1, -1, -1):
        excess = max(cell.bottom for cell in rows[index]) - (below - gaps[index])
        if excess <= 0:
            break
        moves.append((index, excess))
        below = min(cell.top_at(cell.top - excess) for cell in rows[index])
    return moves


def _old_cascade_plan(
    rows: Sequence[list[_Cell]], start: int, top: int, gaps: Sequence[int]
) -> list[tuple[int, int]]:
    moves: list[tuple[int, int]] = []
    floor = top
    for index in range(start, len(rows)):
        row = rows[index]
        if min(cell.top for cell in row) >= floor:
            break
        moves.append((index, floor))
        floor = max(cell.top_at(floor) + cell.geometry.keepout.height for cell in row) + gaps[index]
    return moves


def _old_stack(rows: Sequence[list[_Cell]], row_gap: int, *, top: int) -> None:
    floor = top
    for row in rows:
        for cell in row:
            cell.at_top(floor)
        floor = max(cell.bottom for cell in row) + row_gap


def test_raise_plan_equals_the_old_plan() -> None:
    """The oracle: 600 seeded random columns, every start row, early break included."""
    rng = random.Random(20261005)  # noqa: S311 -- seeded test data
    breaks = 0
    for _ in range(_CASES):
        rows = _rows(rng)
        gaps = [rng.choice([0, 1, 3, 8]) for _ in rows]
        start = rng.randrange(len(rows))
        top = min(c.top for c in rows[start]) - rng.randint(0, 60)
        plan = _raise_plan(rows, start, top, gaps)
        assert plan == _old_raise_plan(rows, start, top, gaps)
        breaks += len(plan) <= start
    assert breaks > 20  # the early break is exercised


def test_cascade_plan_equals_the_old_plan() -> None:
    """600 seeded random columns, lowering from every start row, early break included."""
    rng = random.Random(7)  # noqa: S311 -- seeded test data
    stops = 0
    for _ in range(_CASES):
        rows = _rows(rng)
        gaps = [rng.choice([0, 1, 3, 8]) for _ in rows]
        start = rng.randrange(len(rows))
        top = min(c.top for c in rows[start]) + rng.randint(-5, 60)
        plan = _cascade_plan(rows, start, top, gaps)
        assert plan == _old_cascade_plan(rows, start, top, gaps)
        stops += len(plan) < len(rows) - start
    assert stops > 50


def test_stack_equals_the_old_stack() -> None:
    """600 seeded random columns land on the same origins."""
    rng = random.Random(11)  # noqa: S311 -- seeded test data
    for _ in range(_CASES):
        seed = rng.random()
        a, b = _rows(_rng(seed)), _rows(_rng(seed))
        gap, top = rng.choice([0, 1, 4, 9]), rng.randint(-10, 50)
        _stack(a, gap, top=top)
        _old_stack(b, gap, top=top)
        assert [c.origin for r in a for c in r] == [c.origin for r in b for c in r]
