"""A changeover's throws are alternatives, on demo parts.

`changeover_fixtures.changeover_bus` puts MAIN on the make throws of `q1` and EMERG on its break
throws, behind a two-pole breaker `f1` and a 264 V AC power supply `t1`. The check
"""

import pytest
from changeover_fixtures import changeover_bus
from ratings_fixtures import fn_id

from fransys_model.checks import ALL_VALIDATORS
from fransys_model.checks.ratings import check_ratings
from fransys_model.derive.facts.closure import rail_pairs


def _rating_findings(model):
    return [f for validator in ALL_VALIDATORS for f in validator(model) if "RATING" in f.code]


# -- 1: the consumer's case ----------------------------------------------------------------


def test_a_power_supply_behind_a_changeover_and_a_breaker_gives_no_rating_finding() -> None:
    model, _ = changeover_bus()
    assert check_ratings(model) == ()
    assert _rating_findings(model) == []


def test_the_supply_sees_only_pairs_of_one_supply() -> None:
    model, p = changeover_bus()
    pairs = rail_pairs(model, fn_id(p["t1"], "input"))
    assert pairs == {("M_L1", "M_N"), ("E_L1", "E_L3")}
    assert ("E_L3", "M_L1") not in pairs
    assert ("E_L1", "M_N") not in pairs


def test_without_throw_roles_the_supply_also_sees_the_cross_pairs() -> None:
    model, p = changeover_bus(throw_roles=False)
    pairs = rail_pairs(model, fn_id(p["t1"], "input"))
    assert {("E_L3", "M_L1"), ("E_L1", "M_N")} <= pairs


@pytest.mark.parametrize("pole", ["pole_1", "pole_2"])
def test_a_breaker_pole_on_one_bus_line_sees_no_pair(pole: str) -> None:
    model, p = changeover_bus()
    assert rail_pairs(model, fn_id(p["f1"], pole)) == frozenset()
