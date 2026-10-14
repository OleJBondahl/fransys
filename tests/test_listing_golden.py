"""Listing goldens (LISTING-STABILITY LS1): a text rule that moves a release listing shows here.

`tests/golden/listing/` holds the demo cabinet and board, and `all_moves`, one fixture with a bar,
a lone-cable loom, a tagged instance, a contact block under a head, a cross-unit mate and net and
a terminal strip. A moved golden is a digest move: bump `listing_version`, write the release-note
line, then `just regen-goldens listing`.
"""

import json

import pytest
from listing_golden_cases import GOLDEN_DIR, cases

_CASES = cases()


def test_every_golden_file_has_a_case_and_back() -> None:
    assert {p.name for p in GOLDEN_DIR.glob("*.json")} == set(_CASES)


@pytest.mark.parametrize("name", sorted(_CASES))
def test_the_listing_equals_its_golden(name: str) -> None:
    assert _CASES[name] == (GOLDEN_DIR / name).read_text(encoding="utf-8")


def test_a_bar_end_prints_with_no_screw() -> None:
    """model-0227: the bar's conductor ends read `-PE1`, never `-PE1:1`."""
    listing = json.loads(_CASES["all_moves.C1-unit.json"])
    ends = [e for row in listing["conductors"] for e in (row["a"], row["b"]) if "PE1" in e]
    assert ends == ["-PE1", "-PE1"]


def test_a_contact_block_prints_its_holders_designation() -> None:
    """model-0222: the block's conductor end reads `-S1:11`, the head's designation."""
    listing = json.loads(_CASES["all_moves.C1-unit.json"])
    ends = {e for row in listing["conductors"] for e in (row["a"], row["b"])}
    assert {"-S1:11", "-S1:12"} <= ends
