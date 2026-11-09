"""Tests for core/outline.py: the padded hull around boxes (layout-0300)."""

from dataclasses import replace
from typing import Any

import pytest
from options_fixtures import core_options

from fransys_layout.core.clearance import clear
from fransys_layout.core.errors import CoreError
from fransys_layout.core.geometry import overlaps
from fransys_layout.core.outline import framed, outline_hull, outline_keeps, unit_hulls
from fransys_layout.core.outputs import Outline, PagePlacement, Placed, Placement
from fransys_layout.core.sym_values import Sym, Turned
from fransys_layout.core.values import Box, Facts, Finding, Hints, Options, OutlineRoom, PlacementProblem, Size

from .conftest import MARKER
from .cycle_fixtures import acyclic_problem
from .pipeline_fixtures import solved_of


def test_one_box_grows_by_margin():
    assert outline_hull([Box(10, 20, 30, 40)], 4) == Box(6, 16, 38, 48)


def test_two_apart_boxes_span_both():
    assert outline_hull([Box(0, 0, 10, 10), Box(20, 30, 5, 5)], 2) == Box(-2, -2, 29, 39)


def test_nested_inner_box_is_ignored():
    assert outline_hull([Box(0, 0, 100, 50), Box(10, 10, 5, 5)], 3) == Box(-3, -3, 106, 56)


def test_touching_boxes_join_without_gap():
    assert outline_hull([Box(0, 0, 10, 10), Box(10, 0, 10, 10)], 0) == Box(0, 0, 20, 10)


def test_zero_size_box_is_a_point():
    assert outline_hull([Box(7, 8, 0, 0)], 2) == Box(5, 6, 4, 4)


def test_margin_zero_is_the_box_itself():
    assert outline_hull([Box(10, 20, 30, 40)], 0) == Box(10, 20, 30, 40)


def test_empty_boxes_raise():
    with pytest.raises(CoreError, match="no boxes"):
        outline_hull([], 4)


def test_negative_margin_raises():
    with pytest.raises(CoreError, match="negative"):
        outline_hull([Box(0, 0, 1, 1)], -1)


def test_hull_takes_each_edge_from_whichever_box_reaches_furthest():
    boxes = [Box(10, 0, 10, 10), Box(0, 5, 5, 20)]
    assert outline_hull(boxes, 1) == Box(-1, -1, 22, 27)


def test_outline_hull_is_on_the_core_surface():
    from fransys_layout import core

    assert core.outline_hull is outline_hull


_AREA = Size(400, 300)


def _placed(sym: str, x: int, y: int, w: int = 30, h: int = 40) -> Placed:
    box = Box(x, y, w, h)
    return Placed(sym, 1, x, y, "R0", box, box, ())


_ROOM = OutlineRoom(4, Box(2, 2, 48, 8), Size(64, 48))


def _opts(**given: Any) -> Options:
    return core_options(
        marker=MARKER, tag_stagger=True, label_gap=8, parallel_pitch=48, flip_turn="R180", driver_first=True, arrow_sides=("E", "W"), **given
    )


def _frames(*syms: Placed, members: tuple[str, ...] = ("a", "b"), area: Size = _AREA) -> tuple[tuple[Outline, ...], tuple[Finding, ...]]:
    placement = Placement((PagePlacement(1, syms, (), (), (), ()),))
    problem = PlacementProblem(area, (), (), Facts(), Hints(frames=(("u", frozenset(members)),)))
    return unit_hulls(
        placement,
        problem,
        _opts(outline=_ROOM),
    )


def test_a_unit_frame_is_the_hull_of_its_members_rooms():
    frames, found = _frames(_placed("a", 100, 100), _placed("b", 150, 110, 10, 10), _placed("z", 300, 100))
    assert (frames, found) == ((Outline("u", 1, Box(100, 100, 64, 48), 0),), ())


@pytest.mark.rule("UNIT-OUTLINE")
def test_a_non_member_between_two_members_gives_two_frames_and_neither_holds_it():
    """UNIT-OUTLINES (R1106): one frame per run of members, each with the unit label slot; no frame holds a non-member."""
    frames, found = _frames(_placed("a", 100, 100), _placed("z", 200, 100, 10, 10), _placed("b", 300, 100))
    assert (frames, found) == ((Outline("u", 1, Box(100, 100, 64, 48), 0), Outline("u", 1, Box(300, 100, 64, 48), 1)), ())
    assert not any(f.x < o.box.x + o.box.w and o.box.x < f.x + f.w for o in frames for f in [Box(200, 100, 10, 10)])


def test_a_run_with_a_footprint_too_close_is_named_and_the_other_run_is_drawn():
    frames, found = _frames(_placed("a", 100, 100), _placed("z", 140, 100, 10, 10), _placed("b", 300, 100))
    assert ([o.box.x for o in frames], [f.code for f in found]) == ([300], ["OUTLINE_NO_ROOM"])


def test_a_frame_that_leaves_the_content_box_is_named_and_no_frame_is_drawn():
    frames, found = _frames(_placed("a", -2, 5), _placed("b", 40, 5))
    assert (frames, [f.code for f in found]) == ((), ["OUTLINE_NO_ROOM"])


def test_the_keeps_of_a_frame_are_its_line_and_label_never_its_inside():
    keeps = outline_keeps([Outline("u", 1, Box(100, 100, 80, 60), 0)], _ROOM, 1)
    assert [k.kind for k in keeps] == ["outline"] * 5
    assert clear(Box(179, 120, 2, 2), keeps, {}) != ()
    assert clear(Box(130, 120, 4, 4), keeps, {}) == ()
    assert clear(Box(104, 104, 4, 4), keeps, {}) != ()
    assert outline_keeps([Outline("u", 2, Box(100, 100, 80, 60), 0)], _ROOM, 1) == ()


def test_a_small_unit_frame_grows_to_the_natural_size_of_its_symbol():
    frames, _ = _frames(_placed("a", 100, 100, 10, 10), _placed("b", 112, 100, 10, 10))
    assert [(o.box.w, o.box.h) for o in frames] == [(64, 48)]


def _sym(sid: str) -> Sym:
    box = Box(-8, 0, 16, 32)
    return Sym(sid, None, "", {"": Size(16, 8)}, (), (), {"R0": Turned(box, box, box, (), row_footprint=box)})


def test_a_member_symbol_holds_the_margin_and_the_label_room_only():
    problem = PlacementProblem(_AREA, (_sym("a"), _sym("z")), (), Facts(), Hints(frames=(("u", frozenset({"a"})),)))
    a, z = framed(problem, _opts(outline=_ROOM)).symbols
    assert (a.footprint, a.row_footprint, z.footprint) == (Box(-12, -10, 24, 46), Box(-12, -10, 24, 46), Box(-8, 0, 16, 32))
    assert framed(problem, _opts()) is problem


def test_a_framed_member_keeps_its_neighbour_outside_the_margin_and_label_room():
    """A symbol attached above a member stands 8 off a bare footprint; the frame needs 10 (R1269). Probe: `framed` skipped in `solve`."""
    problem = replace(acyclic_problem(), hints=Hints(frames=(("u", frozenset({"q"})),)))
    placement = solved_of(problem, _opts(outline=_ROOM)).placement
    assert [o.key for o in placement.outlines] == ["u"]
    assert not any(overlaps(placement.outlines[0].box, p.footprint) for p in placement.pages[0].placed if p.sym != "q")
