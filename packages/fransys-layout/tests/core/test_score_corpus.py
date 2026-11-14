"""The scorer on the 17 corpus instances reproduces today's numbers in their `.score.json`."""

import json
from typing import Any

import pytest
from corpus_reader import CORPUS, corpus_names, read_instance, read_score, resided_names

from fransys_layout.core.score import placement_flags, score
from fransys_layout.core.score_wiring import wiring
lazy from fransys_layout.core.outputs import Score

NAMES = corpus_names()


def snapshot(scene, got: Score) -> dict[str, Any]:
    """The scorer's counts of one instance, as stored in `scorer_baseline.json`."""
    return {
        "P": dict(got.P),
        "references": dict(got.R),
        "wiring": wiring(scene.wires),
        "pages": got.pages,
        "symbols": len({b.sym for b in scene.boxes}),
    }


STORED = json.loads((CORPUS / "scorer_baseline.json").read_text(encoding="utf-8"))
READ = {n: read_instance(CORPUS / f"{n}.txt").scene for n in NAMES}  # one read
SCORED = {n: score(READ[n]) for n in NAMES}
FLAGS = {n: placement_flags(READ[n]) for n in NAMES}


@pytest.mark.parametrize("name", NAMES)
def test_references_equal_the_baseline(name: str) -> None:
    assert sum(n for _, n in SCORED[name].R) == read_score(name)["references"]
    assert dict(SCORED[name].R) == STORED["instances"][name]["references"]


@pytest.mark.parametrize("name", NAMES)
def test_wiring_terms_equal_the_baseline(name: str) -> None:
    want, got = read_score(name), wiring(READ[name].wires)
    assert got == {k: want[k] for k in got}


@pytest.mark.parametrize("name", NAMES)
def test_loose_equals_the_baseline_counter(name: str) -> None:
    assert len(FLAGS[name]["loose"]) == read_score(name)["placement"].get("loose", 0)


@pytest.mark.parametrize("name", NAMES)
def test_junction_off_line_equals_the_terminal_counter(name: str) -> None:
    want = read_score(name)["placement"].get("terminal_off_column", 0)
    assert len(FLAGS[name]["junction_off_line"]) == want


@pytest.mark.parametrize("name", [n for n in NAMES if n not in resided_names()])
def test_attached_off_pin_equals_the_coil_counter(name: str) -> None:
    want = read_score(name)["placement"].get("coil_off_channel", 0)
    assert len(FLAGS[name]["attached_off_pin"]) == want


@pytest.mark.parametrize("name", NAMES)
def test_head_off_legs_equals_the_source_counter_except_on_ties(name: str) -> None:
    want = read_score(name)["placement"].get("source_off_loads_page", 0)
    assert len(FLAGS[name]["head_off_legs"]) == want


def test_the_scorer_baseline_file_holds_what_the_scorer_counts_today() -> None:
    """One counter for old and new: the file is the scorer run on today's dumped lines."""
    stored = json.loads((CORPUS / "scorer_baseline.json").read_text(encoding="utf-8"))
    assert stored["instances"] == {n: snapshot(READ[n], SCORED[n]) for n in NAMES}
    assert stored["totals"]["P"] == sum(len(v) for n in NAMES for v in FLAGS[n].values())
