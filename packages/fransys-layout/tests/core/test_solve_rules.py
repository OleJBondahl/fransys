"""IS.1 to IS.7 on the planted problems, and each checker can fail (layout-0296).

A rule a plant misses is a strict xfail with its reason: the designer rules it, nothing is loosened.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Any

import pytest
from options_fixtures import core_options

from fransys_layout.core import PinRef, PlacementProblem
from fransys_layout.core.cut_account_check import account_findings
from fransys_layout.core.outputs import Marker
from fransys_layout.core.solve import solve
from fransys_layout.core.values import Facts, Finding, Hints, RefKind, Size

from . import solve_checks
from .conftest import MARKERS
from .cut_fixtures import elem, net
from .flow_builders import conductors
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
    from fransys_layout.core import Options
    from fransys_layout.core.outputs import CoreLayout

OPTIONS = core_options(
    marker_boxes=MARKERS,
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
    assert check_every_net(solved_of(planted, OPTIONS), planted, OPTIONS) == []


def test_is4_no_overlap(planted: PlacementProblem) -> None:
    assert check_no_overlap(solved_of(planted, OPTIONS), planted, OPTIONS) == []


def test_is5_findings(planted: PlacementProblem) -> None:
    assert check_findings(solved_of(planted, OPTIONS), planted, OPTIONS) == []


def test_is6_plan_is_drawn(planted: PlacementProblem) -> None:
    assert check_plan_drawn(solved_of(planted, OPTIONS)) == []


@pytest.mark.parametrize("form", ["{}", "{:04d}"])
def test_is7_kind_blind(planted: PlacementProblem, form: str) -> None:
    assert check_kind_blind(planted, OPTIONS, form) == []


def test_a_refused_link_is_drawn_as_its_tag_pair_with_room_so_no_net_is_open(monkeypatch: pytest.MonkeyPatch) -> None:
    """The refused n3 is handed to the cut, which plans its tag pair and reserves its room (layout-0508): IS.3 and IS.6 see nothing."""
    _refusing(monkeypatch, (PinRef("b", "s"), PinRef("s", "s"), PinRef("c", "n")))
    prob = ring_beside_a_tall_chain()
    layout = solved_of(prob, OPTIONS)
    assert [r.kind.value for r in layout.references if r.net == "n3"] == ["tag"]
    assert check_every_net(layout, prob, OPTIONS) == []
    assert check_plan_drawn(layout) == []


# ---- each checker can fail -----------------------------------------------------------------------


def test_is1_names_a_solve_that_gives_two_layouts(monkeypatch: pytest.MonkeyPatch) -> None:
    real = solve
    calls: list[int] = []

    def by_call(prob: PlacementProblem, options: Options) -> CoreLayout:
        found = real(prob, options)
        calls.append(1)
        extra = Finding("LABEL_NO_ROOM", "call", len(calls), prob.symbols[0].id)
        return replace(found, findings=(*found.findings, extra))

    monkeypatch.setattr(solve_checks, "solve", by_call)
    msgs = check_pure(ring_beside_a_tall_chain(), OPTIONS)
    assert any("twice" in m for m in msgs)


def test_is2_names_a_missing_and_a_stray_placed(ring) -> None:
    prob, layout = ring
    page, *rest = layout.placement.pages
    broken = replace(layout, placement=replace(layout.placement, pages=(replace(page, placed=page.placed[1:]), *rest)))
    assert [m for m in check_placed_once(broken, prob, OPTIONS) if f"{page.placed[0].sym}: 0" in m]
    stray = replace(page, placed=(*page.placed, replace(page.placed[0], sym="ghost")))
    broken = replace(layout, placement=replace(layout.placement, pages=(stray, *rest)))
    assert "IS.2 ghost: placed but not drawn" in check_placed_once(broken, prob, OPTIONS)


def test_is3_names_an_open_net(ring) -> None:
    prob, layout = ring
    open_net = replace(layout, routes=replace(layout.routes, pages=tuple(replace(pr, wires=()) for pr in layout.routes.pages)))
    assert any(m.startswith("IS.3 n3") for m in check_every_net(open_net, prob, OPTIONS))


def test_is3_names_a_reference_end_without_a_marker() -> None:
    prob = tag_chain()
    layout = solved_of(prob, OPTIONS)
    assert any("marker(s)" in m for m in check_every_net(replace(layout, annotations=replace(layout.annotations, markers=())), prob, OPTIONS))


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
        Finding("LABEL_NO_ROOM", "x", 99),
        Finding("NO_CELL", "x", 1, "zz"),
    )
    msgs = check_findings(replace(layout, findings=bad), prob, OPTIONS)
    assert [m.split(":")[0] for m in msgs] == [
        "IS.5 NOT_A_CODE",
        "IS.5 LABEL_NO_ROOM",
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
            found = replace(found, findings=(Finding("LABEL_NO_ROOM", "x", 1),))
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
    narrow = replace(layout, annotations=bare, findings=(_unplaced_note(f"{first.end.sym},other"),))
    assert check_every_net(replace(layout, annotations=bare, findings=(_unplaced_note(f"{first.end.sym},{first.net}"),)), prob, OPTIONS) == []
    assert any("marker(s)" in m for m in check_every_net(narrow, prob, OPTIONS))


# ---- CORE-ACCOUNT: each end is ink or named, never neither and never both (R2650) ------------------

A, B, C = PinRef("a", "e"), PinRef("b", "e"), PinRef("c", "e")
NETS = ({A: "n", B: "n", C: "n"}, {"a": 1, "b": 1, "c": 1})


def _marker(pin: PinRef, far: PinRef, also: tuple[PinRef, ...] = ()) -> Marker:
    return Marker("n", RefKind.STUB, 1, 0, 0, pin, also=also, far=(far,))


@pytest.mark.rule("CORE-ACCOUNT")
@pytest.mark.parametrize(
    ("pieces", "markers", "stood", "found"),
    [
        ((), (), (), ["not accounted"]),
        ((), (_marker(A, B),), (A,), []),
        ((), (_marker(C, B),), (C,), ["not accounted"]),
        (((A, C),), (_marker(C, B),), (C,), []),
        (((A, B),), (_marker(A, B),), (A,), ["accounted twice"]),
        ((), (_marker(A, B), _marker(A, B)), (A,), ["accounted twice"]),
        ((), (_marker(C, B, also=(A,)),), (C,), ["not accounted"]),
    ],
    ids=["neither", "named", "named-elsewhere", "named-through-a-piece", "wire-and-stub", "two-stubs", "also-not-stood"],
)
def test_core_account_names_an_end_no_carrier_stands_for(pieces: Any, markers: Any, stood: Any, found: list[str]) -> None:
    got = account_findings([(A, B)], pieces, stood, markers, NETS)
    assert [f.text.partition(" of net n ")[2].partition(":")[0] for f in got] == found
    assert {f.code for f in got} <= {"CONNECTION_NOT_ACCOUNTED"}


@pytest.mark.rule("CORE-ACCOUNT")
def test_a_refused_link_the_loop_stands_as_a_pair_leaves_no_end_unaccounted(monkeypatch: pytest.MonkeyPatch) -> None:
    _refusing(monkeypatch, (PinRef("b", "s"), PinRef("s", "s"), PinRef("c", "n")))
    prob = ring_beside_a_tall_chain()
    both = tuple(pair for a, b in conductors(prob.nets) for pair in ((a, b), (b, a)))
    layout = solved_of(replace(prob, facts=replace(prob.facts, far_ends=both)), OPTIONS)
    assert [f.text for f in layout.findings if f.code == "CONNECTION_NOT_ACCOUNTED"] == []


SMALL_PAGE = [  # R3112: nets (x0, x1) over symbols a, b, c on a 240 x 120 page: the cases where the router drew no wire for x0 and said nothing
    (("a.n", "b.n", "c.n"), ("a.s", "b.s")),
    (("a.n", "b.n", "c.n"), ("a.s", "c.s")),
    (("a.n", "b.n", "c.s"), ("a.s", "b.s")),
    (("a.n", "b.n", "c.s"), ("a.s", "c.n")),
    (("a.n", "b.s", "c.n"), ("a.s", "b.n")),
    (("a.n", "b.s", "c.n"), ("a.s", "c.s")),
    (("a.n", "b.n", "c.s"), ("b.s", "c.n")),
    (("a.s", "b.n", "c.s"), ("b.s", "c.n")),
    (("a.n", "b.s", "c.s"), ("a.s", "b.n")),
    (("a.n", "b.s", "c.s"), ("a.s", "c.n")),
    (("a.n", "b.n", "c.n"), ("b.s", "c.s")),
    (("a.s", "b.n", "c.n"), ("b.s", "c.s")),
]


@pytest.mark.rule("CORE-ACCOUNT")
@pytest.mark.parametrize("pins", SMALL_PAGE, ids=["+".join(",".join(n) for n in case) for case in SMALL_PAGE])
def test_a_net_the_router_draws_no_wire_for_is_flagged_or_given_its_fallback(pins: tuple[tuple[str, ...], ...]) -> None:
    nets = [net(f"x{i}", *p) for i, p in enumerate(pins)]
    prob = PlacementProblem(Size(240, 120), tuple(elem(s) for s in "abc"), tuple(nets), Facts(far_ends=conductors(nets)), Hints())
    layout = solved_of(prob)
    assert check_every_net(layout, prob, OPTIONS) == [] or any(f.code == "CONNECTION_NOT_ACCOUNTED" for f in layout.findings)
