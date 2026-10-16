"""`listing_rules`: the rule set a stored version-1 listing was cut under (LS2, model-0289)."""

import pytest

from fransys_model.derive.baseline import (
    OLDEST_VERIFIABLE,
    RULES_BY_RELEASE,
    ListingRules,
    listing_rules,
    rules_moved_in,
)
from fransys_model.derive.baseline_rules import version_key


def test_the_table_is_ordered_oldest_first_and_ends_at_today() -> None:
    keys = [version_key(row.first) for row in RULES_BY_RELEASE]
    assert keys == sorted(keys)
    assert RULES_BY_RELEASE[0].first == OLDEST_VERIFIABLE
    assert RULES_BY_RELEASE[-1].rules == ListingRules()


def test_the_oldest_verifiable_release_has_neither_moved_rule() -> None:
    rules = listing_rules(1, "0.13.8")
    assert rules == ListingRules(
        holder_designation=False, bar_end_without_screw=False, item_keys=False
    )


def test_0_18_2_has_the_holder_rule_only() -> None:
    assert listing_rules(1, "0.18.2") == ListingRules(bar_end_without_screw=False, item_keys=False)


def test_0_18_3_still_prints_the_bar_screw() -> None:
    assert listing_rules(1, "0.18.3") == ListingRules(bar_end_without_screw=False, item_keys=False)


def test_0_18_4_and_later_lack_only_the_item_keys() -> None:
    assert listing_rules(1, "0.18.4") == ListingRules(item_keys=False)
    assert listing_rules(1, "0.19.8") == ListingRules(item_keys=False)


def test_0_20_0_and_later_are_todays_rules() -> None:
    assert listing_rules(2, "0.20.0") == ListingRules()


@pytest.mark.parametrize("version", ["0.13.7", "0.9.0", "", "unreadable"])
def test_a_release_older_than_the_table_has_no_rules(version: str) -> None:
    assert listing_rules(1, version) is None


def test_versions_compare_as_numbers_not_text() -> None:
    assert listing_rules(1, "0.13.14") == listing_rules(1, "0.13.8")
    assert listing_rules(1, "0.13.8") is not None
    assert version_key("0.13.14") > version_key("0.13.8")


def test_another_listing_version_has_no_rules() -> None:
    assert listing_rules(3, "0.19.8") is None


@pytest.mark.parametrize(
    ("version", "moved"),
    [
        ("0.13.8", "0.18.2 and 0.18.4 and 0.20.0"),
        ("0.18.1", "0.18.2 and 0.18.4 and 0.20.0"),
        ("0.18.3", "0.18.4 and 0.20.0"),
        ("0.18.4", "0.20.0"),
    ],
)
def test_the_release_that_moved_each_rule_is_named(version: str, moved: str) -> None:
    rules = listing_rules(1, version)
    assert rules is not None
    assert rules_moved_in(rules) == moved
