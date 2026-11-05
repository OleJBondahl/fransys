"""Self-tests of the label invariant checkers on hand-built labels, then place_labels itself."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from options_fixtures import core_options

from fransys_layout.core import AnnexBox, Box, Size, natural_key
from fransys_layout.core.annex import free, place_labels, spot_box
from fransys_layout.core.annex_values import Annex, Spot
from fransys_layout.core.geometry import inside, overlaps
from fransys_layout.core.values import Finding
from fransys_layout.core.widen import route_round

from . import pipeline_fixtures
from .conftest import MARKER
from .label_fixtures import (
    colliding_neighbours,
    dense,
    house_options,
    lone,
    marker_over_candidate,
    on_page,
    under_wire,
)
from .pipeline_fixtures import with_annexes
from .test_invariants import (
    check_first_free,
    check_label_conflicts,
    check_label_order,
    check_one_label,
)
from .text_fixtures import PLANTS

if TYPE_CHECKING:
    from fransys_layout.core.outputs import Placed

OPTIONS = core_options(
    marker=MARKER,
)
OVER_WIRE = AnnexBox("S1", 1, Box(80, 112, 16, 8), "BL")
ANNEX_UNPLACED = Finding("ANNEX_UNPLACED", "no free corner", page=1, subject="S1")


def _conflicts(case, labels, findings=()):
    """check_label_conflicts on a LabelCase with the given labels and findings."""
    return check_label_conflicts(
        case.placement,
        case.routes,
        case.markers,
        labels,
        findings,
        case.problem.area,
        OPTIONS,
    )


def _first_free(case, labels, findings=()):
    """check_first_free on a LabelCase with the given labels and findings."""
    return check_first_free(
        case.placement,
        case.routes,
        case.markers,
        labels,
        findings,
        with_annexes(case.problem, OPTIONS),
        OPTIONS,
    )


def _cands(case):
    """The (spot, box) list of the case's only symbol: its designation annex's spots at R0."""
    (annex,) = with_annexes(case.problem, OPTIONS).annexes
    placed = case.placement.pages[0].placed[0]
    return [(s.name, spot_box(placed, annex.size, s, 0)) for s in annex.spots[placed.orient]]


def test_one_label_holds_on_lone() -> None:
    case = lone()
    assert check_one_label(case.placement, [OVER_WIRE]) == []


def test_one_label_flags_duplicate() -> None:
    msgs = check_one_label(lone().placement, [OVER_WIRE, OVER_WIRE])
    assert msgs
    assert "S1" in msgs[0]


def test_one_label_flags_missing() -> None:
    msgs = check_one_label(lone().placement, [])
    assert msgs
    assert "S1" in msgs[0]


def test_conflicts_hold_on_lone() -> None:
    case = lone()
    assert _conflicts(case, [AnnexBox("S1", 1, _cands(case)[0][1], "BL")]) == []


def test_conflicts_flags_label_over_wire() -> None:
    msgs = _conflicts(under_wire(), [OVER_WIRE])
    assert msgs
    assert "S1" in msgs[0]


def test_conflicts_accepts_flagged_overlap() -> None:
    assert _conflicts(under_wire(), [OVER_WIRE], [ANNEX_UNPLACED]) == []


def test_conflicts_flags_two_labels_on_one_box() -> None:
    case = colliding_neighbours()
    twin = AnnexBox("S2", 1, Box(80, 112, 16, 8), "BL")
    msgs = _conflicts(case, [OVER_WIRE, twin])
    assert any("S1" in m and "S2" in m for m in msgs)


def test_first_free_holds_at_first_candidate() -> None:
    case = lone()
    corner, box = _cands(case)[0]
    assert _first_free(case, [AnnexBox("S1", 1, box, corner)]) == []


def test_first_free_flags_second_candidate() -> None:
    case = lone()
    corner, box = _cands(case)[1]
    msgs = _first_free(case, [AnnexBox("S1", 1, box, corner)])
    assert msgs
    assert "S1" in msgs[0]


def test_label_order_holds() -> None:
    labels = [
        AnnexBox("S2", 1, Box(0, 0, 16, 8), "BL"),
        AnnexBox("S10", 1, Box(0, 16, 16, 8), "BL"),
    ]
    assert sorted(["S10", "S2"], key=natural_key) == ["S2", "S10"]
    assert check_label_order(lone().placement, labels) == []


def test_label_order_flags_reverse() -> None:
    labels = [
        AnnexBox("S10", 1, Box(0, 16, 16, 8), "BL"),
        AnnexBox("S2", 1, Box(0, 0, 16, 8), "BL"),
    ]
    msgs = check_label_order(lone().placement, labels)
    assert msgs
    assert "S2" in msgs[0]


# Parts B and C: the stage itself.
def _corners(case, options=None):
    labels, findings = case.run(options)
    return {label.owner: label.spot for label in labels}, labels, findings


def test_a_lone_symbol_takes_its_first_corner_at_slack_zero() -> None:
    corners, labels, findings = _corners(lone())
    assert corners == {"S1": "BL"}
    assert labels[0].box == Box(80, 112, 16, 8)
    assert findings == ()


def test_a_symbol_whose_first_corner_is_under_a_wire_takes_the_next() -> None:
    _, labels, findings = _corners(under_wire())
    assert labels[0].box != Box(80, 112, 16, 8)
    assert findings == ()


def test_a_marker_over_the_first_candidate_moves_the_label() -> None:
    _, labels, findings = _corners(marker_over_candidate())
    assert labels[0].box != Box(80, 112, 16, 8)
    assert findings == ()


def test_two_neighbours_do_not_share_a_box() -> None:
    _, labels, findings = _corners(colliding_neighbours())
    assert not overlaps(labels[0].box, labels[1].box)
    assert findings == ()


def test_the_dense_page_reports_text_overlap_and_is_repeatable() -> None:
    first = dense().run()
    assert {f.subject for f in first[1]} == {"S1", "S2", "S3"}
    assert {f.code for f in first[1]} == {"ANNEX_UNPLACED"}
    assert dense().run() == first


def test_corner_order_bl_only_makes_the_neighbours_test_fail() -> None:
    case = colliding_neighbours()
    only = core_options(
        corner_order=("BL",),
        slack=(0,),
        marker=MARKER,
    )
    _, findings = case.run(only)
    assert findings


@pytest.mark.parametrize(("corners", "name"), [(("KL", "KR"), "KL"), (("XX",), "XX")])
def test_an_unknown_corner_names_the_corner_and_the_choices(corners, name) -> None:
    """KL and KR left with text_label_cands (R345): el names them as unknown corners."""
    only = core_options(
        corner_order=corners,
        marker=MARKER,
    )
    with pytest.raises(ValueError, match=rf"unknown label corner '{name}'.*BL"):
        lone().run(only)


@pytest.mark.rule("TEXT-CANDIDATES")
@pytest.mark.parametrize("name", PLANTS)
def test_no_routed_wire_runs_through_a_label_the_router_stood(name: str) -> None:
    """T2: labels stand before the A* round as keeps, so the wires it draws go round them."""
    prob = PLANTS[name]()
    cut = pipeline_fixtures.cut_of(prob, OPTIONS)
    rnd = route_round(cut, pipeline_fixtures.placed_from(cut, prob, OPTIONS), pipeline_fixtures.with_annexes(prob, OPTIONS), OPTIONS)
    routed = [w for page in rnd.routes.pages for w in page.wires if w.kind == "routed"]
    flagged = {f.subject for f in rnd.routes.findings if f.code == "ANNEX_UNPLACED"}
    assert rnd.routes.labels
    assert [lab.owner for lab in rnd.routes.labels if lab.owner not in flagged and not free(lab.box, [], routed, None)] == []


@pytest.mark.rule("TEXT-CANDIDATES")
def test_a_label_stays_at_the_spot_it_stood_at_the_round_before_while_that_spot_is_free() -> None:
    """T2: a label does not move between rounds; without the spot of the round before it takes its first free candidate."""
    case = on_page((("S1", 88, 96),))
    opts = house_options(label_gap=0)
    (annex,) = with_annexes(case.problem, opts).annexes
    placed = {p.sym: p for p in case.placement.pages[0].placed}
    second = annex.spots[placed["S1"].orient][1]
    before = AnnexBox("S1", 1, spot_box(placed["S1"], annex.size, second, 0), second.name)
    ink, on = ((), []), (1, case.problem.area, 0, 2)
    (fresh,), _, _ = place_labels([annex], placed, ink, on)
    (stays,), _, _ = place_labels([annex], placed, ink, on, [before])
    assert fresh.box != before.box
    assert stays == before


@pytest.mark.rule("TEXT-CANDIDATES")
def test_a_label_blocked_at_every_candidate_stands_inside_the_content_box_never_off_the_page() -> None:
    """T6 (AMENDED 1): ANNEX_UNPLACED names it and it stands at its first candidate inside the box, never at one off the page."""
    case = on_page((("S1", 88, 96),))
    placed = {p.sym: p for p in case.placement.pages[0].placed}
    off, near, far = Spot("off", "TL", 1000, 0, "down"), Spot("near", "BL", 0, 0, "down"), Spot("far", "BL", 0, 40, "down")
    annex = Annex("S1", Size(16, 8), None, {"R0": (off, near, far)})
    wall = Box(0, 112, 400, 8)  # a solid across the near candidate
    wall2 = Box(0, 152, 400, 8)  # and across the far one
    area = Size(400, 300)
    (label,), found, blocked = place_labels([annex], placed, ((), [wall, wall2]), (1, area, 0, 2))
    assert [f.code for f in found] == ["ANNEX_UNPLACED"]
    assert blocked == [0]
    assert label.spot == "near"
    assert label.box.x + label.box.w <= area.w


@pytest.mark.rule("TEXT-CANDIDATES")
@pytest.mark.parametrize("name", PLANTS)
def test_no_label_of_a_plant_stands_outside_the_content_box(name: str) -> None:
    """T6 (AMENDED 1): no annex box leaves the content box, blocked or not."""
    prob = PLANTS[name]()
    cut = pipeline_fixtures.cut_of(prob, OPTIONS)
    rnd = route_round(cut, pipeline_fixtures.placed_from(cut, prob, OPTIONS), pipeline_fixtures.with_annexes(prob, OPTIONS), OPTIONS)
    assert rnd.routes.labels
    assert [lab.owner for lab in rnd.routes.labels if not inside(lab.box, prob.area)] == []


def _two_labels() -> tuple[list[Annex], dict[str, Placed]]:
    """S1's first candidate is the only one of S2; S1 has a second above its body."""
    case = on_page((("S1", 88, 96), ("S2", 96, 96)))
    placed = {p.sym: p for p in case.placement.pages[0].placed}
    below, above = Spot("below", "BL", 0, 0, "down"), Spot("above", "TL", 0, -8, "down")
    annexes = [Annex("S1", Size(16, 8), None, {"R0": (below, above)}), Annex("S2", Size(16, 8), None, {"R0": (below,)})]
    return annexes, placed


@pytest.mark.rule("TEXT-CANDIDATES")
def test_a_label_with_no_free_candidate_makes_room_by_moving_the_one_in_its_way() -> None:
    """T3: the first label took the only spot of the second; it gives way to its next, and nothing is flagged."""
    annexes, placed = _two_labels()
    labels, found, blocked = place_labels(annexes, placed, ((), []), (1, Size(400, 300), 0, 2))
    assert (found, blocked) == ([], [])
    assert [(a.owner, a.spot) for a in labels] == [("S1", "above"), ("S2", "below")]
    assert not overlaps(labels[0].box, labels[1].box)
