"""Self-tests of the label invariant checkers on hand-built labels, then place_labels itself."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import pytest
from options_fixtures import core_options

from fransys_layout.core import AnnexBox, Box, Size, natural_key
from fransys_layout.core.anchors import anchor_leads
from fransys_layout.core.annex import place_labels, spot_box
from fransys_layout.core.annex_values import Annex, Spot
from fransys_layout.core.errors import CoreError
from fransys_layout.core.geometry import inside, overlaps, union
from fransys_layout.core.outputs import Anchored, Demand, StripRun
from fransys_layout.core.route_labels import roomed
from fransys_layout.core.route_runs import alone_annexes, named, stand_runs
from fransys_layout.core.values import Finding
from fransys_layout.core.widen import route_round

from . import pipeline_fixtures
from .conftest import MARKER
from .label_fixtures import (
    bl_first_options,
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
    free,
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


def test_first_free_holds_at_a_candidate() -> None:
    case = lone()
    corner, box = _cands(case)[0]
    assert _first_free(case, [AnnexBox("S1", 1, box, corner)]) == []


def test_first_free_flags_a_label_off_its_candidates() -> None:
    case = lone()
    corner, box = _cands(case)[1]
    assert _first_free(case, [AnnexBox("S1", 1, box, corner)]) == []
    msgs = _first_free(case, [AnnexBox("S1", 1, Box(box.x + 1, box.y, box.w, box.h), corner)])
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


def test_corner_order_bl_only_leaves_one_neighbour_to_the_turned_rungs() -> None:
    """With one corner the neighbours collide there; the turned rungs (5, 6, 11) take the label that cannot stand (R1849)."""
    case = colliding_neighbours()
    only = core_options(
        corner_order=("BL",),
        marker=MARKER,
    )
    _, labels, findings = _corners(case, only)
    assert any(label.turned for label in labels)
    assert findings == ()


@pytest.mark.parametrize(("corners", "name"), [(("KL", "KR"), "KL"), (("XX",), "XX")])
def test_an_unknown_corner_names_the_corner_and_the_choices(corners, name) -> None:
    """KL and KR left with text_label_cands (R345): el names them as unknown corners."""
    only = core_options(
        corner_order=corners,
        marker=MARKER,
    )
    with pytest.raises(ValueError, match=rf"unknown label corner '{name}'.*BL"):
        lone().run(only)


@pytest.mark.rule("TAG-CORNERS")
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


@pytest.mark.rule("TAG-CORNERS")
@pytest.mark.parametrize("name", PLANTS)
def test_a_label_stands_only_at_a_candidate_it_was_given_or_is_named_unplaced(name: str) -> None:
    """LABEL-PLACE 5: the distance gate is the ladder; place_labels invents no spot, so no label stands further away than a given one."""
    prob = PLANTS[name]()
    cut = pipeline_fixtures.cut_of(prob, OPTIONS)
    placement = pipeline_fixtures.placed_from(cut, prob, OPTIONS)
    annexed = pipeline_fixtures.with_annexes(prob, OPTIONS)
    rnd = route_round(cut, placement, annexed, OPTIONS)
    placed = {p.sym: p for page in placement.pages for p in page.placed}
    mine = {a.owner: a for a in annexed.annexes}
    assert rnd.routes.labels
    for lab in rnd.routes.labels:
        at = placed[lab.owner]
        given = [spot_box(at, mine[lab.owner].size, s, 0) for s in mine[lab.owner].spots[at.orient]]
        assert lab.box in given, (lab.owner, lab.box)


@pytest.mark.rule("TAG-CORNERS")
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


@pytest.mark.rule("TAG-CORNERS")
def test_a_blocked_label_demands_its_first_rung_and_the_owner_footprint_holds_it() -> None:
    """R1831: the Demand is the first rung inside the content box, relative to the owner; roomed puts it into every view's footprint."""
    case = on_page((("S1", 88, 96),))
    placed = {p.sym: p for p in case.placement.pages[0].placed}
    annex = Annex("S1", Size(16, 8), None, {"R0": (Spot("near", "BL", 0, 0, "down"), Spot("far", "BL", 0, 40, "down"))})
    walls = [Box(0, 112, 400, 8), Box(0, 152, 400, 8)]
    _, _, asks = place_labels([annex], placed, ((), walls), (1, Size(400, 300), 0, 2))
    demand = asks[0]
    here = placed["S1"]
    assert demand.owner == "S1"
    assert demand.box == Box(here.body.x - here.x, here.body.y + here.body.h - here.y, 16, 8)
    sym = next(s for s in roomed(case.problem, [demand]).symbols if s.id == "S1")
    assert all(union(v.footprint, demand.box) == v.footprint for v in sym.views.values())


@pytest.mark.rule("TAG-CORNERS")
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
    assert list(blocked) == [0]
    assert label.spot == "near"
    assert label.box.x + label.box.w <= area.w


@pytest.mark.rule("TAG-CORNERS")
def test_a_label_whose_only_free_spot_is_turned_stands_there_with_the_turned_box() -> None:
    """Acceptance 3: the upright spot is walled; the turned one is free and its box is the turned size."""
    case = on_page((("S1", 88, 96),))
    placed = {p.sym: p for p in case.placement.pages[0].placed}
    upright = Spot("up", "BL", 0, 0, "down")
    side = Spot("side", "TL", -8, 0, "down", turned=True)
    annex = Annex("S1", Size(16, 8), None, {"R0": (upright, side)}, Size(8, 16))
    wall = Box(0, 112, 400, 8)  # across the upright spot only
    (label,), found, _ = place_labels([annex], placed, ((), [wall]), (1, Size(400, 300), 0, 2))
    assert found == []
    assert (label.spot, label.turned) == ("side", True)
    assert (label.box.w, label.box.h) == (8, 16)
    assert not overlaps(label.box, wall)


@pytest.mark.rule("TAG-CORNERS")
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


@pytest.mark.rule("TAG-CORNERS")
def test_a_label_with_no_free_candidate_makes_room_by_moving_the_one_in_its_way() -> None:
    """T3: the first label took the only spot of the second; it gives way to its next, and nothing is flagged."""
    annexes, placed = _two_labels()
    labels, found, blocked = place_labels(annexes, placed, ((), []), (1, Size(400, 300), 0, 2))
    assert (found, blocked) == ([], {})
    assert [(a.owner, a.spot) for a in labels] == [("S1", "above"), ("S2", "below")]
    assert not overlaps(labels[0].box, labels[1].box)


def _runs_case(*, blocked: bool = False):
    """Strip `S`: T1, T2 side by side at y 96, T3 alone at y 200: two runs, T1 and T3 leftmost; `blocked` covers the page with a solid."""
    base = on_page((("T1", 88, 96), ("T2", 140, 96), ("T3", 88, 200)))
    syms = tuple(replace(s, row_group="S") for s in base.problem.symbols)
    problem = with_annexes(replace(base.problem, symbols=syms), bl_first_options())
    placed = {p.sym: p for p in base.placement.pages[0].placed}
    lone = (StripRun("S", ("T1", "T2"), "S run at T1"), StripRun("S", ("T3",), "S run at T3"))
    tags, runs = stand_runs(problem, placed, lone)
    members = alone_annexes(
        [replace(a, alone=replace(a, size=Size(40, 8))) if a.owner == "T3" else a for a in problem.annexes if a.owner in placed], lone
    )
    stood = {**placed, **{k: p for k, (_, p) in runs.items()}}
    ink = ((), [Box(0, 0, 400, 300)] if blocked else [])
    return runs, named(runs, *place_labels([*members, *tags], stood, ink, (1, problem.area, 0, 2)))


@pytest.mark.rule("STRIP-TAG-ONCE")
def test_a_strip_gets_one_tag_per_run_of_two_and_a_lone_terminal_its_full_annex() -> None:
    """Two terminals of one strip at one y are one run with one strip annex; the one at another y has none and stands with its own full annex."""
    runs, (labels, found, _) = _runs_case()
    assert [p.sym for _, p in runs.values()] == ["T1"]
    assert [a.owner for a in labels].count("S") == 1
    assert {a.owner for a in labels} == {"S", "T1", "T2", "T3"}
    assert next(a for a in labels if a.owner == "T3").box.w == 40
    assert found == []


@pytest.mark.rule("STRIP-TAG-ONCE")
def test_a_run_tag_that_cannot_stand_is_unplaced_naming_the_strip_and_demands_its_leftmost_terminal() -> None:
    """No silent fallback: the finding names the strip, the Demand its run's leftmost terminal so that its footprint holds the room."""
    _, (_, found, asks) = _runs_case(blocked=True)
    assert [f.subject for f in found].count("S") == 1
    assert {d.owner for d in asks.values()} == {"T1", "T2", "T3"}


@pytest.mark.rule("STRIP-TAG-ONCE")
def test_a_run_of_a_strip_with_no_template_annex_is_refused_naming_the_strip() -> None:
    """No silent skip: a run whose strip has no Annex owned by the strip raises."""
    base = on_page((("T1", 88, 96),))
    placed = {p.sym: p for p in base.placement.pages[0].placed}
    with pytest.raises(CoreError, match="strip S"):
        stand_runs(base.problem, placed, (StripRun("S", ("T1", "T2"), "S run at T1"),))


@pytest.mark.rule("TAG-CORNERS")
def test_an_anchors_lead_is_wire_ink_from_its_pin_to_its_port() -> None:
    lead = ((88, 112), (88, 120))
    (wire,) = anchor_leads((Anchored("S1", "1", 1, 88, 120, "R0", Box(80, 120, 16, 8), (88, 120), lead),))
    assert (wire.points, wire.page, wire.kind) == (lead, 1, "straight")


@pytest.mark.rule("TAG-CORNERS")
def test_a_room_demand_grows_the_owner_footprint_on_its_own_side() -> None:
    """R1961: a south room holds G below the cell, a north room above; any other side is refused, never grown above by default."""
    case = on_page((("S1", 88, 96),))
    before = {o: v.footprint for o, v in next(s for s in case.problem.symbols if s.id == "S1").views.items()}
    for side, up, down in (("N", 16, 0), ("S", 0, 16)):
        sym = next(s for s in roomed(case.problem, [Demand("", 0, 16, "S1", side=side)]).symbols if s.id == "S1")
        for o, v in sym.views.items():
            old = before[o]
            assert old is not None
            assert v.footprint == Box(old.x, old.y - up, old.w, old.h + up + down)
    with pytest.raises(CoreError, match="only N and S"):
        roomed(case.problem, [Demand("", 0, 16, "S1", side="E")])
