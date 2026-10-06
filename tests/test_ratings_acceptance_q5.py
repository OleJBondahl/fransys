"""RATINGS-1 part 6, acceptance 5: Q5 (a unit's boundary values) and ruling (a), on demo parts.

Unit `ub`'s boundary connector `xb` states a rating; unit `ua` declares supply `DC` (800 V and 0 V)
and wires its own connector to `xb` (`ratings_fixtures_units.units_model`). The finding of a
boundary rating names the unit and stands wherever the unit sits: beside the supply's unit, inside
it, or in a build that holds no supply, where nothing is checked.

Can-fail probes, each one Edit, run and undone: `function_ratings` skipping the boundaries
(`vocab/rating_readers.py`) fails the boundary-rating tests; `voltage.common_reference` true for
two earthed AC supplies fails the two-supplies test.
"""

import sys
from decimal import Decimal
from pathlib import Path

import pytest

from fransys_model.kernel import Severity
from fransys_model.vocab.ratings import Operating
from fransys_model.vocab.validators.ratings import RATING_VOLTAGE_BELOW_CIRCUIT, check_ratings

_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    # `--import-mode=importlib` (root pyproject.toml) never puts this folder on `sys.path`.
    sys.path.insert(0, str(_TESTS_DIR))

from ratings_fixtures_units import dc, two_earthed_supplies_model, units_model  # noqa: E402


@pytest.mark.parametrize("nested", [False, True], ids=["side-by-side", "nested"])
@pytest.mark.parametrize(("volts", "fires"), [("600", True), ("1000", False)])
def test_a_boundary_rating_below_the_rails_of_another_unit_fires_and_names_the_unit(
    volts: str, *, nested: bool, fires: bool
) -> None:
    built = units_model(nested=nested, rating=dc(volts))
    found = check_ratings(built.model)
    if not fires:
        assert found == ()
        return
    (finding,) = found
    assert finding.code == RATING_VOLTAGE_BELOW_CIRCUIT
    assert finding.severity is Severity.ERROR
    assert finding.subjects == (built.boundary_fn,)
    assert "boundary rating of unit" in finding.message
    assert "part or template rating" not in finding.message
    assert all(text in finding.message for text in ("'x1'", "600", "800", "'+800'", "'0V'"))


def test_a_receiving_unit_that_states_its_limit_and_declares_no_supply_gives_no_finding() -> None:
    built = units_model(feed=False, rating=dc("600"), lamp_dc="100")
    assert check_ratings(built.model) == ()


def test_the_same_unit_inside_a_design_that_declares_the_supply_finds_the_inside_item() -> None:
    built = units_model(rating=dc("1000"), lamp_dc="100")
    assert built.lamp_fn is not None
    (finding,) = check_ratings(built.model)
    assert finding.subjects == (built.lamp_fn,)
    assert "part or template rating" in finding.message
    assert "'lamp'" in finding.message
    assert "100" in finding.message
    assert "800" in finding.message


def test_a_boundary_with_only_an_operating_envelope_gives_no_finding_on_the_rails() -> None:
    built = units_model(operating=Operating(voltage_dc_v=Decimal(24)))
    assert check_ratings(built.model) == ()


@pytest.mark.parametrize(("volts", "fires"), [("400", True), ("500", False)])
def test_two_earthed_ac_supplies_stand_at_the_sum_across_l1_and_x1(
    volts: str, *, fires: bool
) -> None:
    """Declared phases compare only within one supply: 230 + 230 V, not 0 V at phase 0 and 0."""
    model, lamp_fn = two_earthed_supplies_model(volts)
    found = check_ratings(model)
    if not fires:
        assert found == ()
        return
    (finding,) = found
    assert finding.subjects == (lamp_fn,)
    assert "460" in finding.message
    assert "'L1'" in finding.message
    assert "'X1'" in finding.message
