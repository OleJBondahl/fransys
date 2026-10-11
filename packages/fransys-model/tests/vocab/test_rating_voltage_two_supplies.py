"""`RATING_VOLTAGE_BELOW_CIRCUIT` across two supplies (decision model-0081, model review Q4).

Declared phases compare only within one supply: independent sources keep no fixed phase relation.
So AC rails of two supplies, earthed or IT, check at the sum of their voltages to earth; DC rails
of two earthed supplies keep their difference; rails of one supply keep today's formulas.
"""

from typing import TYPE_CHECKING

from plant import Plant
from rating_plant import load, rail, rated, supply

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
