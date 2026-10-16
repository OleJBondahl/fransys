"""Self-tests of the label invariant checkers on hand-built labels; label_pages is not called."""

from __future__ import annotations

import pytest

from fransys_layout.core import Box, Options, natural_key, text_labels
from fransys_layout.core.geometry import overlaps
from fransys_layout.core.occupancy import Occupancy
from fransys_layout.core.outputs import Label
from fransys_layout.core.text_label_cands import candidates
from fransys_layout.core.text_labels import Cover, descend, first_pass
from fransys_layout.core.values import Finding

from .conftest import MARKER_BOX
from .label_fixtures import (
    colliding_neighbours,
    dense,
    lone,
    marker_over_candidate,
    under_wire,
    with_slot,
)
from .test_invariants import (
    check_first_free,
    check_label_conflicts,
    check_label_order,
    check_one_label,
)

OVER_WIRE = Label("S1", 1, Box(80, 112, 16, 8), "BL")
TEXT_OVERLAP = Finding("TEXT_OVERLAP", "no free corner", page=1, subject="S1")


def _conflicts(case, labels, findings=()):
    """check_label_conflicts on a LabelCase with the given labels and findings."""
    return check_label_conflicts(
        case.placement,
        case.routes,
        case.markers,
        case.tables,
        labels,
        findings,
        case.problem.area,
        Options(marker=MARKER_BOX),
    )


def _first_free(case, labels, findings=()):
    """check_first_free on a LabelCase with the given labels and findings."""
    return check_first_free(
        case.placement,
        case.routes,
        case.markers,
        case.tables,
        labels,
        findings,
        case.problem,
        Options(marker=MARKER_BOX),
    )


def _cands(case):
    """The candidate list of the case's only symbol."""
    sym = case.problem.symbols[0]
    placed = case.placement.pages[0].placed[0]
    return candidates(sym, placed, Options(marker=MARKER_BOX))


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
    assert _conflicts(case, [Label("S1", 1, _cands(case)[0][1], "BL")]) == []


def test_conflicts_flags_label_over_wire() -> None:
    msgs = _conflicts(under_wire(), [OVER_WIRE])
    assert msgs
    assert "S1" in msgs[0]


def test_conflicts_accepts_flagged_overlap() -> None:
    assert _conflicts(under_wire(), [OVER_WIRE], [TEXT_OVERLAP]) == []


def test_conflicts_flags_two_labels_on_one_box() -> None:
    case = colliding_neighbours()
    twin = Label("S2", 1, Box(80, 112, 16, 8), "BL")
    msgs = _conflicts(case, [OVER_WIRE, twin])
    assert any("S1" in m and "S2" in m for m in msgs)


def test_first_free_holds_at_first_candidate() -> None:
    case = lone()
    corner, box = _cands(case)[0]
    assert _first_free(case, [Label("S1", 1, box, corner)]) == []


def test_first_free_flags_second_candidate() -> None:
    case = lone()
    corner, box = _cands(case)[1]
    msgs = _first_free(case, [Label("S1", 1, box, corner)])
    assert msgs
    assert "S1" in msgs[0]


def test_label_order_holds() -> None:
    labels = [Label("S2", 1, Box(0, 0, 16, 8), "BL"), Label("S10", 1, Box(0, 16, 16, 8), "BL")]
    assert sorted(["S10", "S2"], key=natural_key) == ["S2", "S10"]
    assert check_label_order(lone().placement, labels) == []


def test_label_order_flags_reverse() -> None:
    labels = [Label("S10", 1, Box(0, 16, 16, 8), "BL"), Label("S2", 1, Box(0, 0, 16, 8), "BL")]
    msgs = check_label_order(lone().placement, labels)
    assert msgs
    assert "S2" in msgs[0]


# Parts B and C: the stage itself.
def _corners(case, options=None):
    labels, findings = case.run(options)
    return {label.owner: label.corner for label in labels}, labels, findings


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


def test_a_slot_candidate_comes_first() -> None:
    corners, _, _ = _corners(with_slot())
    assert corners == {"S1": "KL"}


def test_the_dense_page_reports_text_overlap_and_is_repeatable() -> None:
    first = dense().run()
    assert {f.subject for f in first[1]} == {"S1", "S2", "S3"}
    assert {f.code for f in first[1]} == {"TEXT_OVERLAP"}
    assert dense().run() == first


def test_corner_order_bl_only_makes_the_neighbours_test_fail() -> None:
    case = colliding_neighbours()
    only = Options(corner_order=("BL",), slack=(0,), marker=MARKER_BOX)
    _, findings = case.run(only)
    assert findings


def test_a_slot_only_corner_order_without_a_slot_names_the_symbol_and_the_fix() -> None:
    only = Options(corner_order=("KL", "KR"), marker=MARKER_BOX)
    with pytest.raises(
        ValueError, match=r"no label candidate for symbol 'S1'.*add BL, TL, BR or TR"
    ):
        lone().run(only)


def test_an_unknown_corner_names_the_corner_and_the_choices() -> None:
    bad = Options(corner_order=("XX",), marker=MARKER_BOX)
    with pytest.raises(ValueError, match=r"unknown label corner 'XX'.*BL"):
        lone().run(bad)


def _crowd() -> tuple[Cover, list[list[tuple[str, Box]]]]:
    """A's first candidate is free but is B's only one; A's second is free for A alone."""
    cover = Cover(Occupancy(20, 20, 8))
    a1, a2, b1 = Box(0, 0, 16, 8), Box(0, 64, 16, 8), Box(8, 0, 16, 8)
    return cover, [[("BL", a1), ("TL", a2)], [("BL", b1)]]


def test_descent_moves_the_blocking_label_and_clears_the_count() -> None:
    cover, cands = _crowd()
    first_pass(cover, cands)
    assert cover.choice == [0, 0]
    assert cover.blocked(cands[1][0][1]) > 0
    assert descend(cover, cands) == 1
    assert cover.choice == [1, 0]
    assert max(cover.held.values()) == 1


def test_no_rounds_leave_the_crowded_first_pass(monkeypatch) -> None:
    monkeypatch.setattr(text_labels, "ROUNDS", 0)
    cover, cands = _crowd()
    first_pass(cover, cands)
    assert descend(cover, cands) == 0
    assert cover.choice == [0, 0]
