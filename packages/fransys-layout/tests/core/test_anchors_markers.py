"""TRUNK-CLEAR item 3a (layout-0394): an anchored item keeps clear of the page's marker boxes."""

from __future__ import annotations

from dataclasses import replace

import pytest

from fransys_layout.core import widen
from fransys_layout.core.anchors import _fit, _marker_keeps, anchor_misses, anchor_pages
from fransys_layout.core.outputs import Anchored, Marker, PagePlacement, PinXY, Placed, Placement, Routes
from fransys_layout.core.values import Anchor, Box, PinRef, PlacementProblem, Pose, RefKind

from .test_solve_anchor_rounds import _options, _problem

OPTIONS = _options(0)
FRAME = Box(-200, -200, 800, 800)
PAGE = PagePlacement(1, (), (), (), (), ())
# R0 marker at (100, 40): the box (100, 32, 48, 16)
STUB = Marker("N1", RefKind.COPY, 1, "c", 100, 40, PinRef("K1", "A1"))
ON_STUB = Pose("R90", (0, 0), Box(96, 28, 16, 28), (0, 0))
BESIDE = Pose("R270", (0, 0), Box(148, 28, 16, 28), (0, 0))  # touches the stub's right edge


def test_the_marker_box_is_the_one_home_box() -> None:
    assert _marker_keeps(1, [STUB], OPTIONS)[0].box == Box(100, 32, 48, 16)
    assert _marker_keeps(2, [STUB], OPTIONS) == ()


def test_a_pose_on_a_marker_box_is_skipped_for_the_next() -> None:
    marks = _marker_keeps(1, [STUB], OPTIONS)
    assert _fit([ON_STUB, BESIDE], (0, 0), PAGE, marks, FRAME) is BESIDE


def test_with_no_markers_the_first_pose_stands() -> None:
    assert _fit([ON_STUB, BESIDE], (0, 0), PAGE, (), FRAME) is ON_STUB


def _item(outline: Box) -> Anchored:
    return Anchored("K1", "1", 1, 0, 0, "R90", outline, (0, 0), ((0, 0), (0, 0)))


def test_an_outline_on_a_marker_box_is_a_miss_and_a_touching_one_is_not() -> None:
    placement = Placement((PAGE,))
    on = anchor_misses(placement, (_item(Box(96, 28, 16, 28)),), _problem(), OPTIONS, [STUB])
    off = anchor_misses(placement, (_item(Box(148, 28, 16, 28)),), _problem(), OPTIONS, [STUB])
    assert [h for _, h in on] == [["marker"]]
    assert off == ()


NEAR = Box(-8, -40, 16, 16)


def _placed(sym: str, y: int) -> Placed:
    return Placed(sym, 1, 100, y, "R0", Box(100, y, 16, 32), Box(100, y, 16, 32), (PinXY("1", 108, y),))


def _anchors_over(*ys: tuple[str, int], outline: Box = NEAR) -> tuple[PlacementProblem, Placement]:
    pose = Pose("R90", (0, -40), outline, (0, -40))
    problem = replace(_problem(), anchors=tuple(Anchor(PinRef(sym, "1"), (("N", pose),)) for sym, _ in ys))
    page = PagePlacement(1, tuple(_placed(sym, y) for sym, y in ys), (), (), (), ())
    return problem, Placement((page,))


@pytest.mark.rule("G08-POWER")
def test_anchors_are_posed_by_pin_position_not_by_id() -> None:
    problem, placement = _anchors_over(("K1", 300), ("K2", 200))
    posed, found = anchor_pages(placement, problem, OPTIONS)
    assert [a.sym for a in posed] == ["K2", "K1"]
    assert found == ()


@pytest.mark.rule("G08-POWER")
def test_an_anchor_that_fits_nowhere_is_a_finding_that_names_it(monkeypatch: pytest.MonkeyPatch) -> None:
    problem, placement = _anchors_over(("K1", 300), outline=Box(-2000, -40, 16, 16))
    posed, found = anchor_pages(placement, problem, OPTIONS)
    assert [(f.code, f.subject, f.page) for f in found] == [("PLACEMENT_PROBLEM", "K1", 1)]
    assert "K1/1" in found[0].text
    assert "enlarge the page or split the unit" in found[0].text
    assert len(posed) == 1
    monkeypatch.setattr(widen, "route_pages", lambda *_: Routes((), (), ()))
    assert [f.code for f in widen.routed(placement, None, problem, OPTIONS, widen.Standing([], {})).findings] == ["PLACEMENT_PROBLEM"]  # ty: ignore[invalid-argument-type] - the stub never reads the cut
