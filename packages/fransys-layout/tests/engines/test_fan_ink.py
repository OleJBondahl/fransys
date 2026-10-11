"""Layout-0172 round 3: a side fan's ink and texts keep off the symbol, its tag and its bundle.

The three cabinet drawings that hold a side fan (house sheet, narrow sheet, second location)
are laid out once; each rule reads the finished pages (`fan_ink`).
"""

from functools import cache
from itertools import pairwise
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

from fan_ink import (
    bundle_lines_off_their_apex,
    bundle_over_cores,
    ink_along_outlines,
    ink_over_symbols,
    splits_on_foreign_keepouts,
    texts_in_fan_outlines,
)
from layout_cabinet import build_cabinet
from narrow_cabinet import narrow_model, narrow_results

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.geometry import Point, through
from fransys_model.kernel import freeze

if TYPE_CHECKING:
    from fransys_layout.engines.schematic.engine import StageResults


@cache
def _every() -> tuple[StageResults, ...]:
    models = (
        freeze(build_cabinet()),
        narrow_model(158),
        freeze(build_cabinet(second_location=True)),
    )
    return tuple(stage_results(model, read_inputs(model))[0] for model in models)


def test_no_core_or_bundle_line_runs_along_a_symbols_outline() -> None:
    assert [one for results in _every() for one in ink_along_outlines(results)] == []


def test_no_core_or_bundle_line_runs_over_a_symbols_ink_on_any_page() -> None:
    assert [one for results in _every() for one in ink_over_symbols(results)] == []


def test_no_fan_split_stands_on_another_symbols_keepout() -> None:
    assert [one for results in _every() for one in splits_on_foreign_keepouts(results)] == []


def test_no_tag_or_line_label_stands_inside_a_fans_outline() -> None:
    assert [one for results in _every() for one in texts_in_fan_outlines(results)] == []


def test_no_bundle_line_runs_over_a_core() -> None:
    assert [one for results in _every() for one in bundle_over_cores(results)] == []


def test_each_fanned_branch_has_one_bundle_line_ending_at_its_apex() -> None:
    assert [one for results in _every() for one in bundle_lines_off_their_apex(results)] == []


def _stub(*, fan_at: Point, legs: list[list[Point]], lines: list[list[Point]]) -> StageResults:
    harness = "h"
    fan = SimpleNamespace(
        harness=harness,
        branch=1,
        drawing_set=1,
        page=1,
        at=fan_at,
        legs=[SimpleNamespace(points=points) for points in legs],
    )
    drawn = [
        SimpleNamespace(harness=harness, branch=1, drawing_set=1, page=1, points=points)
        for points in lines
    ]
    return cast("StageResults", SimpleNamespace(lines=SimpleNamespace(fan_outs=[fan], lines=drawn)))


def _at(x: int, y: int) -> Point:
    return Point(x=x, y=y)


def test_the_bundle_checks_can_fail_on_a_hand_built_page() -> None:
    leg = [_at(8, 0), _at(0, 8), _at(0, 16)]
    over = _stub(fan_at=_at(8, 0), legs=[leg], lines=[[_at(8, 0), _at(8, 8), _at(-8, 8)]])
    assert len(bundle_over_cores(over)) == 0
    over = _stub(fan_at=_at(8, 0), legs=[leg], lines=[[_at(8, 0), _at(0, 0), _at(0, 12)]])
    assert len(bundle_over_cores(over)) == 1
    short = _stub(fan_at=_at(8, 0), legs=[leg], lines=[[_at(16, 0), _at(40, 0)]])
    assert len(bundle_lines_off_their_apex(short)) == 1
    two = _stub(
        fan_at=_at(8, 0), legs=[leg], lines=[[_at(8, 0), _at(40, 0)], [_at(8, 0), _at(8, 9)]]
    )
    assert len(bundle_lines_off_their_apex(two)) == 1


def test_no_cable_box_stands_on_a_wire() -> None:
    """The narrow sheet's lone core: its cable box sat across a wire, its bundle over a contact.

    `WIRE_OVER_LABEL` covers a stub's box: a route runs through it, and a bundle line counts as
    a wire too (CABLE-BOX-SELF): a bundle ends at its box's edge and never crosses it.
    """
    findings = narrow_results(158)[1]
    assert [f.message for f in findings if f.code == "WIRE_OVER_LABEL"] == []


def test_no_bundle_line_runs_through_a_stub_box() -> None:
    lines = narrow_results(158)[0].lines
    assert [
        f"{line.harness} line {line.branch} on page {line.page}: {seg} through {stub.box}"
        for stub in lines.stubs
        for line in lines.lines
        if (line.drawing_set, line.page) == (stub.drawing_set, stub.page)
        for seg in pairwise(line.points)
        if through(seg, stub.box)
    ] == []
