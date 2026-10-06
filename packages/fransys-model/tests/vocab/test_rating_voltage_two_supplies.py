"""`RATING_VOLTAGE_BELOW_CIRCUIT` across two supplies (decision model-0081, model review Q4).

Declared phases compare only within one supply: independent sources keep no fixed phase relation.
So AC rails of two supplies, earthed or IT, check at the sum of their voltages to earth; DC rails
of two earthed supplies keep their difference; rails of one supply keep today's formulas.
"""

from fractions import Fraction
from typing import TYPE_CHECKING

import pytest
from plant import Plant
from rating_plant import AC_400, load, rail, rated, supply

from fransys_model.vocab import voltage
from fransys_model.vocab.enums import Current
from fransys_model.vocab.validators.ratings import check_ratings

if TYPE_CHECKING:
    from fransys_model.kernel import Finding


def _two_ac(rating: str) -> list[Finding]:
    """A load on `L1` of the earthed supply `a` and `L1B` of the earthed supply `b`, both 230 V."""
    plant = Plant()
    supply(plant, "a", {"L1": rail("230", 0)})
    supply(plant, "b", {"L1B": rail("230", 0)})
    load(plant, "d", [("L1",), ("L1B",)], rated(ac=rating))
    return list(check_ratings(plant.model()))


def test_two_earthed_ac_supplies_at_one_phase_stand_at_the_sum_not_at_zero() -> None:
    (finding,) = _two_ac("400")
    assert finding.message == (
        "function 'f' of item d is rated 400 V AC (part or template rating), "
        "but rails 'L1' and 'L1B' stand across it at 460 V "
        "(two AC supplies, no fixed phase: the sum of their voltages to earth)"
    )
    assert _two_ac("500") == []


def test_the_sum_of_two_supplies_fires_strictly_above_the_rating_only() -> None:
    assert _two_ac("460") == []
    assert len(_two_ac("459")) == 1


def test_two_rails_of_one_ac_supply_keep_the_phase_formula() -> None:
    """L1 and L3 of one supply stand at the square root of 158,700 (398.4), not at 460."""
    plant = Plant()
    supply(plant, "ac", AC_400)
    load(plant, "d", [("L1",), ("L3",)], rated(ac="400"))
    assert check_ratings(plant.model()) == ()
    tight = Plant()
    supply(tight, "ac", AC_400)
    load(tight, "d", [("L1",), ("L3",)], rated(ac="398"))
    (finding,) = check_ratings(tight.model())
    assert "stand across it at 398.4 V" in finding.message
    assert "supplies" not in finding.message


def _two_dc(first: str, second: str, rating: str) -> int:
    """A load on `X` (`first` volts) of the earthed DC supply `x` and `Y` of the earthed `y`."""
    plant = Plant()
    supply(plant, "x", {"X": rail(first)}, current=Current.DC)
    supply(plant, "y", {"Y": rail(second)}, current=Current.DC)
    load(plant, "d", [("X",), ("Y",)], rated(dc=rating))
    return len(check_ratings(plant.model()))


def test_two_earthed_dc_supplies_keep_the_difference() -> None:
    assert (_two_dc("24", "-24", "50"), _two_dc("24", "-24", "48")) == (0, 0)
    assert (_two_dc("24", "-24", "47.99"), _two_dc("24", "-24", "40")) == (1, 1)


def test_two_earthed_dc_rails_of_equal_value_in_two_supplies_stand_at_zero() -> None:
    assert _two_dc("24", "24", "1") == 0
    assert _two_dc("24", "24", "0") == 0


def _rail_v(supply_name: str, *, ac: bool, it: bool) -> voltage.RailV:
    value = Fraction(230)
    return voltage.RailV("R", supply_name, it, ac, value, 0 if ac else None, voltage.exact(value))


@pytest.mark.parametrize(
    ("first", "second", "expected"),
    [
        (_rail_v("s", ac=True, it=False), _rail_v("s", ac=True, it=False), True),
        (_rail_v("s", ac=True, it=True), _rail_v("s", ac=True, it=True), True),
        (_rail_v("x", ac=False, it=False), _rail_v("y", ac=False, it=False), True),
        (_rail_v("x", ac=True, it=False), _rail_v("y", ac=True, it=False), False),
        (_rail_v("x", ac=True, it=False), _rail_v("y", ac=True, it=True), False),
        (_rail_v("x", ac=False, it=False), _rail_v("y", ac=False, it=True), False),
    ],
    ids=[
        "one-supply",
        "one-it-supply",
        "two-earthed-dc",
        "two-earthed-ac",
        "earthed-and-it-ac",
        "dc-one-it",
    ],
)
def test_common_reference_is_one_supply_or_two_earthed_dc_supplies(
    first: voltage.RailV, second: voltage.RailV, *, expected: bool
) -> None:
    assert voltage.common_reference(first, second) is expected
