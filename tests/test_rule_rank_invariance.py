"""RANK-INVARIANCE (R568, R571; spec s3): the core's result does not depend on the text of any id.

Seam level (s3.1), no salts. For every build of the reference-lane corpus and `bank_model(40)`,
each problem handed to `lay_out_core.solve` is solved as it is and with every id kind permuted
"""

import importlib
from functools import cache
from typing import Any

import pytest
from _core_solves import caught_solves
from _rank_outcome import outcome
from _rank_rename import (
    build_mapping,
    check_all_mapped,
    rename_options,
    rename_problem,
    unrename,
)
from _rank_salt_runner import run
from _reference_lane_runner import _cases
from fransys_el import lay_out_core

from fransys_layout.core.arrow_reserve import leg_depth, leg_fit, leg_rows
from fransys_layout.core.band import trunk_room
from fransys_layout.core.cut_end_rooms import arrow_room
from fransys_layout.core.topology import build_flow

# Builds here show DANGLING_WIRE_END (KI-414) at the salts (R1219, R1174 anchors); CONNECTION_NOT_DRAWN is 0 (KI-413 closed, R1736).
pytestmark = [pytest.mark.rule("RANK-INVARIANCE"), pytest.mark.private_input]  # internal/ (R462)

_NAMES = (
    "distribution_board",
    "machine_panel",
    "mcc",
    "panel_di16p",
    "remote_io",
    "demo-skid",
    "bank40",
)


def _builds() -> dict[str, Any]:
    ring = importlib.import_module("ring_cases")
    return {**_cases(), "bank40": lambda: ring.bank_model(40)}


@pytest.fixture(scope="module", params=_NAMES)
def solves(request: pytest.FixtureRequest) -> list[tuple[Any, Any, Any]]:
    """The (problem, options, layout) of each set the build solves; built once per module."""
    return _solved(request.param)


@cache
def _solved(name: str) -> list[tuple[Any, Any, Any]]:
    """A second `fr.build` of the same case is cached and solves nothing, so build once."""
    return caught_solves(_builds()[name])[1]


def _small() -> tuple[Any, Any, Any]:
    return _solved("machine_panel")[0]


def _differs(solves_: list[tuple[Any, Any, Any]], mode: str) -> list[tuple[int, list[str]]]:
    out: list[tuple[int, list[str]]] = []
    for n, (problem, options, layout) in enumerate(solves_):
        renamed, mapping = rename_problem(problem, mode)
        assert mode == "control" or any(k != v for k, v in mapping.items())
        again = lay_out_core.solve(renamed, rename_options(options, mapping))
        before, after = outcome(layout), outcome(unrename(again, mapping))
        out.append((n, [k for k in before if before[k] != after[k]]))
    return out


def test_the_builds_are_the_corpus_plus_bank_model() -> None:
    """A build added to the reference lane joins this test, or the list says why not."""
    assert sorted(_builds()) == sorted(_NAMES)


def test_reversing_the_ids_of_every_set_leaves_the_layout_as_it_was(
    solves: list[tuple[Any, Any, Any]],
) -> None:
    """Pages, positions, wires, markers, references and finding codes equal, set by set."""
    assert solves
    for mode in ("reverse", "shuffle"):
        assert [(n, d) for n, d in _differs(solves, mode) if d] == [], mode


def test_the_control_respelling_leaves_the_layout_as_it_was(
    solves: list[tuple[Any, Any, Any]],
) -> None:
    """Every id with a prefix: no comparison changes, so `unrename` must give the same layout."""
    assert [(n, d) for n, d in _differs(solves, "control") if d] == []


def test_renaming_twice_gives_the_problem_back() -> None:
    """The reversal is an involution: its own mapping applied to the result is the identity."""
    problem = _small()[0]
    once, mapping = rename_problem(problem)
    twice, _ = rename_problem(once)
    assert once != problem
    assert twice == problem
    assert unrename(once, mapping) == problem


def test_the_two_permutations_move_every_kind_and_differ_from_each_other() -> None:
    """The xfail hides a harness that renames nothing, so this plain test holds the harness."""
    problem = _small()[0]
    reverse = build_mapping(problem, "reverse")
    shuffle = build_mapping(problem, "shuffle")
    assert sum(k != v for k, v in reverse.items()) > len(reverse) // 2
    assert sum(k != v for k, v in shuffle.items()) > len(shuffle) // 2
    assert sum(reverse[k] != shuffle[k] for k in reverse) > len(reverse) // 2


def test_a_mapping_that_misses_a_net_is_caught() -> None:
    """The harness fails on an id it cannot reach rather than leaving it unrenamed."""
    problem = _small()[0]
    _, mapping = rename_problem(problem)
    check_all_mapped(problem, mapping)
    missing = dict(mapping)
    del missing[problem.nets[0].id]
    with pytest.raises(AssertionError, match="no mapping"):
        check_all_mapped(problem, missing)


_SALTS = ("a", "b", "c", "d", "e")


@cache
def _salted(salt: str, name: str) -> list[Any]:
    """One build under the default ids or one salt, in a context of its own (R550), so the sweep sees each build (R1219)."""
    return run(salt, name)


@pytest.mark.parametrize("name", _NAMES)
@pytest.mark.parametrize("salt", _SALTS)
def test_a_salt_draws_the_same_drawing_up_to_ids(salt: str, name: str) -> None:
    """Spec s3.2, R1371: each salt's layouts of every corpus build equal the default ids', with the id hashes taken out."""
    assert _salted(salt, name) == _salted("-", name)


@pytest.mark.rule("SYMBOL-TIE")
def test_bank40_markers_and_hub_choice_are_equal_at_salts_default_and_d() -> None:
    """R1504: the markers (order, stands, the hub a copy names) of the bank-of-40 build are the default ids' under salt d."""
    default, other = _salted("-", "bank40"), _salted("d", "bank40")
    assert default
    assert [lay["markers"] for lay in other] == [lay["markers"] for lay in default]


@pytest.mark.parametrize("salt", ["-", *_SALTS])
def test_bank40_overflows_no_page_and_strands_no_leg_at_any_salt(salt: str) -> None:
    """R1673: the cut reserves the legs its placement stands, so the bank of 40 has no page over, no row too wide and one head off its legs."""
    laid = _salted(salt, "bank40")
    codes = {entry.split("*")[0] for lay in laid for entry in lay["findings"]}
    assert laid
    assert not codes & {"PAGE_OVERFLOW", "OUT_OF_PAGE", "WIDER_THAN_PAGE"}
    # KI-636, R1735: R1719's arrow room makes rows taller, so one head's page holds 18 of 40 legs; every leg is joined (looks)
    assert [entry for lay in laid for entry in lay["findings"] if entry.startswith("HEAD_OFF_LEGS")] == ["HEAD_OFF_LEGS*1"]


def test_bank40_trunks_with_legs_hold_their_leg_depth_in_the_room_the_row_keeps() -> None:
    """R1647, R1719: a trunk's `room` is `trunk_room` of `leg_depth` (its tallest leg marker or arrow room), and the solved row keeps that room."""
    problem, options, layout = _solved("bank40")[0]
    fans = {f.id: f for f in build_flow(problem, options).fans}
    plans = {p.page: p for p in layout.pages}
    deep = False
    for page in layout.placement.pages:
        stood = leg_rows(layout.references, page.page)
        fit = leg_fit(options, layout.references, page.page)
        for t in page.trunks:
            fan = fans[t.fan]
            arrow = arrow_room(layout.references, plans[page.page], [fan], t.row, options)
            depth = leg_depth(fan, stood, t.row, fit, arrow)
            assert t.room == trunk_room(t.lanes, options.wiring_grid, depth)
            assert t.room[1] <= page.bands[t.row][1] - t.y  # the solved row keeps what the trunk says it holds
            deep = deep or depth > 0
    assert deep
