"""TALL-PAGE T5 (layout-0167): the height decision reuses the width re-plan pass (C21).

A page set with no tall group plans pages exactly as many times as before; a tall group adds
no pass of its own when the widths grew, and one when only it asks. All data invented.
"""

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from layout_cabinet import build_cabinet
from samples import hid
lazy import pytest

from fransys_layout.engines.schematic import engine
from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.geometry import Box
from fransys_layout.stages.middle_fold import GroupShape
from fransys_layout.stages.references.digits import SetDigits
from fransys_model.kernel import freeze

FLOOR = 854
UNIT = hid("unit", 1)


def test_the_cabinet_with_no_tall_group_plans_its_pages_twice_as_before(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The cabinet's widths grow once (C21): two plans, the cut pass is not a third."""
    calls: list[int] = []
    plan = engine.plan_pages
    monkeypatch.setattr(engine, "plan_pages", lambda *args: (calls.append(1), plan(*args))[1])
    model = freeze(build_cabinet())
    stage_results(model, read_inputs(model))
    assert len(calls) == 2


@dataclass(frozen=True)
class _Inputs:
    middle: dict[Any, Any]
    sheet: Any


@dataclass(frozen=True)
class _Run:
    inputs: _Inputs


@dataclass(frozen=True)
class _Group:
    unit: Any
    upper: frozenset[Any]
    lower: frozenset[Any]
    cut: bool = False
    frame_dx: int = 0
    below: bool = False


def _middle(*, lower: bool) -> dict[Any, Any]:
    group = _Group(SimpleNamespace(unit=UNIT), frozenset({"u"}), frozenset({"l"} if lower else ()))
    return {"u": (group,), "l": (group,)}


def _shape(bottom: int) -> GroupShape:
    box = Box(x=0, y=0, width=0, height=0)
    return GroupShape(UNIT, UNIT, 1, 1, box, box, (), bottom=bottom)


def _passes(
    monkeypatch: pytest.MonkeyPatch, *, bottom: int, grew: bool, lower: bool = True
) -> list[Any]:
    """The `middle` each `plan_pages` call saw, with `place_pages` stubbed to one folded shape."""
    seen: list[Any] = []

    def plan(run: Any, *_: Any) -> Any:
        seen.append(run.inputs.middle)
        return SimpleNamespace(plans=(), columns=())

    page = (None, SimpleNamespace(shapes=[_shape(bottom)]))
    decided = (
        SimpleNamespace(digits=(SetDigits(drawing_set=1, refs=2, sheets=2),), markers=()),
        (),
    )
    widths = ("grown",) if grew else ()
    monkeypatch.setattr(engine, "plan_pages", plan)
    monkeypatch.setattr(
        engine, "place_pages", lambda *_: (SimpleNamespace(drawn=(), pages=[page]), widths, decided)
    )
    run: Any = _Run(_Inputs(_middle(lower=lower), SimpleNamespace(content_height=FLOOR)))
    nothing: Any = None  # the stubs read none of the drawn or the decide
    engine._placed(run, (), (), (), nothing)
    return seen


def test_no_tall_group_and_no_grown_width_plans_once(monkeypatch: pytest.MonkeyPatch) -> None:
    assert len(_passes(monkeypatch, bottom=FLOOR, grew=False)) == 1


def test_no_tall_group_leaves_the_second_pass_to_the_widths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert len(_passes(monkeypatch, bottom=FLOOR, grew=True)) == 2


def test_a_tall_group_rides_the_width_pass_and_asks_for_one_only_when_alone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """UNDO: `_placed` re-plans on `grown != widths` alone, so a tall group is never cut."""
    assert len(_passes(monkeypatch, bottom=FLOOR + 1, grew=True)) == 2
    assert len(_passes(monkeypatch, bottom=FLOOR + 1, grew=False)) == 2


def test_a_tall_group_recut_would_hold_costs_no_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    """UNDO: `tall_groups` passes a group with no lower band, and the engine re-plans for it."""
    assert len(_passes(monkeypatch, bottom=FLOOR + 1, grew=False, lower=False)) == 1
