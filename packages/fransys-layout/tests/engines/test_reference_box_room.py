"""S4, layout-0143: a reference box wider than the room its pass reserved is one finding.

Gap 1: a set of 100 `#n` numbers draws a 3-digit `#n` in a band sized for the floor's two.
Gap 2: a set whose page count crosses 99 to 100 between the two passes draws a wider `p<sheet>`
than the column widths the first pass sized. All data invented.
"""

from functools import cache
from types import SimpleNamespace
from typing import Any

from layout_cabinet import build_cabinet
from samples import hid, page_plan
from star_nets import star_nets
lazy import pytest

from fransys_layout.engines.schematic import engine
from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.lint.codes import ALL_CODES, REFERENCE_BOX_EXCEEDS_ROOM
from fransys_layout.stages.references import box_room_findings
from fransys_layout.stages.references.digits import SetDigits
from fransys_layout.stages.types import MarkerSide
from fransys_model.kernel import Finding, Severity, freeze


@cache
def _hundred() -> tuple[Finding, ...]:
    """The findings of the 100-star fixture, built once for this module (a build is 3 s)."""
    model = star_nets(100)
    return stage_results(model, read_inputs(model))[1]


def _room(findings: tuple[Finding, ...]) -> list[Finding]:
    return [one for one in findings if one.code == REFERENCE_BOX_EXCEEDS_ROOM]


def test_a_set_of_a_hundred_reference_groups_is_reported_once() -> None:
    """Gap 1: 100 `#n` numbers draw `#100` in a two-digit band; one finding names its ends."""
    # CAN-FAIL: stages/references/room_check.py `box_room_findings`: `one.refs > FLOOR.refs` ->
    #     `one.refs > FLOOR.refs + 1` (the refs room is judged one digit too wide) fails here
    found = _room(_hundred())
    assert len(found) == 1
    assert found[0].severity is Severity.WARNING
    assert len(found[0].subjects) == 100
    assert "3-digit #n" in found[0].message


def test_a_set_that_fits_its_room_is_not_reported() -> None:
    """The cabinet's reference boxes stand in the room reserved: no finding, so it is no noise."""
    model = freeze(build_cabinet())
    assert not _room(stage_results(model, read_inputs(model))[1])


def test_the_code_is_one_of_the_packages_codes() -> None:
    """`ALL_CODES` lists it, so the scan test and the guide table know it."""
    assert REFERENCE_BOX_EXCEEDS_ROOM in ALL_CODES


def _decided(digits: SetDigits) -> Any:
    """A `References` as far as the check reads it: one set's digits and one reference end."""
    end = SimpleNamespace(
        port=hid("port", 1), drawing_set=1, symbol="", star="", side=MarkerSide.OWNER
    )
    return SimpleNamespace(digits=(digits,), markers=(end,)), ()


def _plans(count: int) -> Any:
    return tuple(page_plan(("a",), number=n) for n in range(1, count + 1))


def test_a_sheet_count_that_grew_a_digit_is_reported() -> None:
    """Gap 2, stage level: the first pass planned 99 sheets, the final decisions say 100."""
    # CAN-FAIL: stages/references/room_check.py `box_room_findings`: `one.sheets > reserved.get(`
    #     -> `one.sheets < reserved.get(` (the sheets room compared the wrong way) fails here
    _, found = box_room_findings(_decided(SetDigits(drawing_set=1, refs=2, sheets=3)), _plans(99))
    assert [one.code for one in found] == [REFERENCE_BOX_EXCEEDS_ROOM]
    assert found[0].subjects == (hid("port", 1),)


def test_a_sheet_count_that_kept_its_digits_is_not_reported() -> None:
    """The same final digits against a first pass that already held 100 sheets: silent."""
    assert (
        box_room_findings(_decided(SetDigits(drawing_set=1, refs=2, sheets=3)), _plans(100))[1]
        == ()
    )
    assert (
        box_room_findings(_decided(SetDigits(drawing_set=1, refs=2, sheets=2)), _plans(99))[1] == ()
    )


def test_the_engine_holds_the_first_pass_plans_as_the_sheets_room(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`_placed` judges the final pass against the pass-1 plans, not its own."""
    # CAN-FAIL: engines/schematic/engine.py `_placed`: `box_room_findings(decided, first)` ->
    #     `(decided, planned.plans)` (the room is the final plans' own) fails here
    passes = iter((_plans(99), _plans(100)))
    monkeypatch.setattr(
        engine, "plan_pages", lambda *_: SimpleNamespace(plans=next(passes), columns=())
    )
    calls = iter((("grown",), ()))
    final = _decided(SetDigits(drawing_set=1, refs=2, sheets=3))
    monkeypatch.setattr(
        engine,
        "place_pages",
        lambda *_: (SimpleNamespace(drawn=(), pages=[]), next(calls), final),
    )
    nothing: Any = None  # the stubs read none of the drawn or the decide
    sheet = SimpleNamespace(content_height=854)  # no page, so no group is tall
    run: Any = SimpleNamespace(inputs=SimpleNamespace(sheet=sheet, middle={}))
    _, (_, found) = engine._placed(run, (), (), (), nothing)
    assert [one.code for one in found] == [REFERENCE_BOX_EXCEEDS_ROOM]
