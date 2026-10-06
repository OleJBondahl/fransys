"""CONTACT-STATES acceptance 1 and 2: a changeover's throws are alternatives, on demo parts.

`changeover_fixtures.changeover_bus` puts MAIN on the make throws of `q1` and EMERG on its break
throws, behind a two-pole breaker `f1` and a 264 V AC power supply `t1`. Acceptance 1: the check
gives nothing at `t1` and `f1`. The control is the same wiring on a changeover whose ports have no
throw roles, which gives the false finding, so the silence is not one the check cannot break.
Acceptance 2: a pole of `q1` itself still sees both supplies across its open gap.

Can-fail probes, each one Edit, run and undone: `link_state` returning `"both"` for every link
(`vocab/contacts.py`) fails the acceptance 1 tests; a rail's starting condition at an end of a
contact link holding that link's state (`_rail_states` in `vocab/closure.py`) fails the
acceptance 2 test.
"""

import sys
from pathlib import Path

import pytest

from fransys_model.kernel import Severity
from fransys_model.vocab.closure import rail_pairs
from fransys_model.vocab.validators import ALL_VALIDATORS
from fransys_model.vocab.validators.ratings import RATING_VOLTAGE_BELOW_CIRCUIT, check_ratings

_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    # `--import-mode=importlib` (root pyproject.toml) never puts this folder on `sys.path`.
    sys.path.insert(0, str(_TESTS_DIR))

from changeover_fixtures import changeover_bus  # noqa: E402
from ratings_fixtures import fn_id, rated  # noqa: E402


def _rating_findings(model):
    return [f for validator in ALL_VALIDATORS for f in validator(model) if "RATING" in f.code]


# -- 1: the consumer's case ----------------------------------------------------------------


def test_a_power_supply_behind_a_changeover_and_a_breaker_gives_no_rating_finding() -> None:
    model, _ = changeover_bus()
    assert check_ratings(model) == ()
    assert _rating_findings(model) == []


def test_with_no_throw_roles_the_false_finding_is_on_the_supply_and_the_breaker() -> None:
    model, p = changeover_bus(throw_roles=False)
    found = check_ratings(model)
    assert {f.code for f in found} == {RATING_VOLTAGE_BELOW_CIRCUIT}
    assert {f.severity for f in found} == {Severity.ERROR}
    assert {f.subjects for f in found} == {
        (fn_id(p["t1"], "input"),),
        (fn_id(p["f1"], "pole_1"),),
        (fn_id(p["f1"], "pole_2"),),
    }
    assert all("628.7" in f.message for f in found)


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


# -- 2: the pole's own open gap ------------------------------------------------------------


@pytest.mark.parametrize(("volts", "fires"), [("628", True), ("629", False)])
def test_a_changeover_pole_stands_across_both_supplies_at_628_7_volts(
    volts: str, *, fires: bool
) -> None:
    """MAIN's L1 at the make throw and EMERG's L1 at the break throw: the open gap holds both."""
    model, p = changeover_bus()
    assert rail_pairs(model, fn_id(p["q1"], "co_1")) == {("E_L1", "M_L1")}
    found = check_ratings(rated(model, "DEMO-CO-4P-24", "co_1", voltage_ac_v=volts))
    if not fires:
        assert found == ()
        return
    (finding,) = found
    assert finding.code == RATING_VOLTAGE_BELOW_CIRCUIT
    assert finding.subjects == (fn_id(p["q1"], "co_1"),)
    assert all(text in finding.message for text in ("'co_1'", "'E_L1'", "'M_L1'", "628.7"))
