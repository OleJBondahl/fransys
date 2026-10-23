"""IS.1 to IS.7 on the planted problems, and each checker can fail (layout-0296).

A rule a plant misses is a strict xfail with its reason: the designer rules it, nothing is loosened.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import pytest
from options_fixtures import core_options

from fransys_layout.core.solve import solve
from fransys_layout.core.values import Finding

from . import solve_checks
from .conftest import MARKER
from .pipeline_fixtures import solved_of
from .solve_checks import (
    check_every_net,
    check_findings,
    check_kind_blind,
    check_no_overlap,
    check_placed_once,
    check_plan_drawn,
    check_pure,
)
from .solve_fixtures import ring_beside_a_tall_chain, two_unit_crossing_nets
from .test_fallbacks import _refusing
from .test_solve import PLANTS
from .text_fixtures import tag_chain

if TYPE_CHECKING:
    from fransys_layout.core import Options, PlacementProblem
    from fransys_layout.core.outputs import CoreLayout

OPTIONS = core_options(
    marker=MARKER,
    flip_turn="R180",
    tag_stagger=True,
    label_gap=8,
    parallel_pitch=48,
    driver_first=True,
    arrow_sides=("E", "W"),
)
ALL = {**PLANTS, "two_unit_crossing_nets": two_unit_crossing_nets}


@pytest.fixture(params=sorted(ALL))
def planted(request: pytest.FixtureRequest) -> PlacementProblem:
    return ALL[request.param]()


@pytest.fixture(scope="module")
def ring() -> tuple[PlacementProblem, CoreLayout]:
    prob = ring_beside_a_tall_chain()
    return prob, solved_of(prob, OPTIONS)


def test_is1_pure(planted: PlacementProblem) -> None:
    assert check_pure(planted, OPTIONS) == []


def test_is2_placed_once(planted: PlacementProblem) -> None:
    assert check_placed_once(solved_of(planted, OPTIONS), planted, OPTIONS) == []


def test_is3_every_net(planted: PlacementProblem) -> None:
    assert check_every_net(solved_of(planted, OPTIONS), planted) == []


def test_is4_no_overlap(planted: PlacementProblem) -> None:
    assert check_no_overlap(solved_of(planted, OPTIONS), planted, OPTIONS) == []


def test_is5_findings(planted: PlacementProblem) -> None:
    assert check_findings(solved_of(planted, OPTIONS), planted, OPTIONS) == []


def test_is6_plan_is_drawn(planted: PlacementProblem) -> None:
    assert check_plan_drawn(solved_of(planted, OPTIONS)) == []


@pytest.mark.parametrize("form", ["{}", "{:04d}"])
def test_is7_kind_blind(planted: PlacementProblem, form: str) -> None:
    assert check_kind_blind(planted, OPTIONS, form) == []


def test_is3_names_a_refused_link_open_with_no_tag_to_hide_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The refused n3 is open on its page and gets no tag pair: IS.3 sees it (R424)."""
    from .test_fallbacks import ENDS

    _refusing(monkeypatch, ENDS)
    prob = ring_beside_a_tall_chain()
    layout = solved_of(prob, OPTIONS)
    assert [r.kind.value for r in layout.references if r.net == "n3"] == []
    assert check_every_net(layout, prob) == []
    assert check_plan_drawn(layout) == []


# ---- each checker can fail -----------------------------------------------------------------------


def test_is1_names_a_solve_that_depends_on_the_input_order(monkeypatch: pytest.MonkeyPatch) -> None:
    real = solve

    def by_order(prob: PlacementProblem, options: Options) -> CoreLayout:
        found = real(prob, options)
        extra = Finding("TEXT_OVERLAP", "order", 1, prob.symbols[0].id)
        return replace(found, findings=(*found.findings, extra))

    monkeypatch.setattr(solve_checks, "solve", by_order)
    msgs = check_pure(ring_beside_a_tall_chain(), OPTIONS)
    assert any("reversing" in m for m in msgs)


def test_is2_names_a_missing_and_a_stray_placed(ring) -> None:
    prob, layout = ring
    page, *rest = layout.placement.pages
    lost = replace(page, placed=page.placed[1:])
    broken = replace(layout, placement=replace(layout.placement, pages=(lost, *rest)))
    assert [m for m in check_placed_once(broken, prob, OPTIONS) if f"{page.placed[0].sym}: 0" in m]
    stray = replace(page, placed=(*page.placed, replace(page.placed[0], sym="ghost")))
    broken = replace(layout, placement=replace(layout.placement, pages=(stray, *rest)))
    assert "IS.2 ghost: placed but not drawn" in check_placed_once(broken, prob, OPTIONS)


def test_is3_names_an_open_net(ring) -> None:
    prob, layout = ring
    bare = tuple(replace(pr, wires=()) for pr in layout.routes.pages)
    open_net = replace(layout, routes=replace(layout.routes, pages=bare))
    assert any(m.startswith("IS.3 n3") for m in check_every_net(open_net, prob))


def test_is3_names_a_reference_end_without_a_marker() -> None:
    prob = tag_chain()
    layout = solved_of(prob, OPTIONS)
    unmarked = replace(layout, annotations=replace(layout.annotations, markers=()))
    assert any("marker(s)" in m for m in check_every_net(unmarked, prob))


def test_is4_names_two_bodies_that_overlap(ring) -> None:
    prob, layout = ring
    page, *rest = layout.placement.pages
    first, second, *others = page.placed
    moved = replace(second, body=first.body)
    broken = replace(page, placed=(first, moved, *others))
    layout = replace(layout, placement=replace(layout.placement, pages=(broken, *rest)))
    assert any("hard boxes overlap" in m for m in check_no_overlap(layout, prob, OPTIONS))


def test_is5_names_a_foreign_code_page_and_subject(ring) -> None:
    prob, layout = ring
    bad = (
        Finding("NOT_A_CODE", "x"),  # ty: ignore[invalid-argument-type] -- the foreign code is the point
        Finding("TEXT_OVERLAP", "x", 99),
        Finding("NO_CELL", "x", 1, "zz"),
    )
    msgs = check_findings(replace(layout, findings=bad), prob, OPTIONS)
    assert [m.split(":")[0] for m in msgs] == [
        "IS.5 NOT_A_CODE",
        "IS.5 TEXT_OVERLAP",
        "IS.5 NO_CELL",
    ]


def test_is6_names_a_class_whose_markers_do_not_match_the_plan() -> None:
    layout = solved_of(tag_chain(), OPTIONS)
    fewer = replace(layout.annotations, markers=layout.annotations.markers[:-1])
    assert check_plan_drawn(replace(layout, annotations=fewer))


def test_is7_names_a_solve_that_reads_an_id_spelling(monkeypatch: pytest.MonkeyPatch) -> None:
    real = solve

    def reads_spelling(prob: PlacementProblem, options: Options) -> CoreLayout:
        found = real(prob, options)
        if not prob.symbols[0].id.islower():
            found = replace(found, findings=(Finding("TEXT_OVERLAP", "x", 1),))
        return found

    monkeypatch.setattr(solve_checks, "solve", reads_spelling)
    assert check_kind_blind(ring_beside_a_tall_chain(), OPTIONS)


def _unplaced_note(subject: str) -> Finding:
    return Finding("MARKER_UNPLACED", f"tag marker at {subject}: no place", 1, subject)


def test_is3_exempts_only_the_end_a_marker_unplaced_names_r449() -> None:
    prob = tag_chain()
    layout = solved_of(prob, OPTIONS)
    first = layout.annotations.markers[0]
    bare = replace(layout.annotations, markers=layout.annotations.markers[1:])
    exact = _unplaced_note(f"{first.end.sym},{first.net}")
    same_symbol_other_net = _unplaced_note(f"{first.end.sym},other")
    assert check_every_net(replace(layout, annotations=bare, findings=(exact,)), prob) == []
    narrow = replace(layout, annotations=bare, findings=(same_symbol_other_net,))
    assert any("marker(s)" in m for m in check_every_net(narrow, prob))
