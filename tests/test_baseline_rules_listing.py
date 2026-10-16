"""`listing(model, unit, rules=...)` cuts the text under the rules that moved (LS2, model-0289).

Today's rules give the bytes the goldens hold; each rule off gives the text of the release
that predates it. The fixture is `listing_golden_cases._all_moves`, built once.
"""

import json

import pytest
from listing_golden_cases import _all_moves

from fransys_model.derive import baseline
from fransys_model.derive.baseline_unchecked import UNPRINTABLE
from fransys_model.vocab.tables import units

_MODEL = _all_moves()
_C1 = next(uid for uid, u in units(_MODEL).items() if u.key == ("C1", "unit"))


def _ends(rules: baseline.ListingRules) -> set[str]:
    listing = json.loads(baseline.dumps(baseline.listing(_MODEL, _C1, rules)))
    return {e for row in listing["conductors"] for e in (row["a"], row["b"])}


@pytest.mark.parametrize("unit", [None, _C1])
def test_default_rules_are_todays_rules(unit: object) -> None:
    today = baseline.dumps(baseline.listing(_MODEL, unit))  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]  # parametrised Id or None
    assert today == baseline.dumps(baseline.listing(_MODEL, unit, baseline.ListingRules()))  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]  # parametrised Id or None


def test_a_bar_end_reads_with_its_screw_before_0_18_4() -> None:
    ends = _ends(baseline.ListingRules(bar_end_without_screw=False))
    assert "-PE1:1" in ends
    assert "-PE1" not in ends


def test_a_bar_end_reads_without_its_screw_today() -> None:
    assert "-PE1" in _ends(baseline.ListingRules())


def test_a_contact_block_reads_its_holders_designation_today() -> None:
    assert {"-S1:11", "-S1:12"} <= _ends(baseline.ListingRules())


def test_an_untagged_block_cannot_print_before_0_18_2_and_is_marked_unprintable() -> None:
    """The block was numbered then; today's model holds no number for it: its ends are marked."""
    ends = _ends(baseline.ListingRules(holder_designation=False))
    assert {f"{UNPRINTABLE}:11", f"{UNPRINTABLE}:12"} <= ends
    assert "-S1:11" not in ends


def _keys(listing_version: int, fransys: str) -> bool:
    rules = baseline.listing_rules(listing_version, fransys)
    assert rules is not None
    return rules.item_keys


def test_a_listing_carries_item_keys_from_0_20_0_and_its_own_version_says_so():
    assert _keys(1, "0.19.8") is False
    assert _keys(2, "0.20.0") is True
    assert _keys(2, "0.19.8") is True
    assert _keys(1, "0.20.0") is False
    assert baseline.listing_rules(3, "0.20.0") is None


def test_a_v1_listing_rules_name_0_20_0_as_the_release_that_moved_the_keys():
    stored = baseline.listing_rules(1, "0.19.8")
    assert stored is not None
    assert baseline.rules_moved_in(stored) == "0.20.0"
