"""`RATING_VOLTAGE_BELOW_CIRCUIT` with IT supplies (decision model-0079, model review Q4 and Q2).

An IT rail's voltage to earth is its supply's highest voltage between two of its own rails; a pair
across an IT supply and another has no common reference and stands at the sum of the two rails'
voltages to earth. Every model is hand-built and invented.
"""

from fractions import Fraction
from typing import TYPE_CHECKING

from plant import Plant
from rating_plant import load, rail, rated, supply

from fransys_model.vocab import voltage
from fransys_model.vocab.enums import Earthing
from fransys_model.vocab.validators.ratings import check_ratings

if TYPE_CHECKING:
    from fransys_model.kernel import Finding

EARTHED, IT = Earthing.EARTHED, Earthing.IT
# Two rails of 100 V at 0 and 60 degrees: 100 V apart, exactly, so a boundary can be hit.
SQUARE_IT = {"A": rail("100", 0), "B": rail("100", 60)}


def _run(plant: Plant) -> tuple[Finding, ...]:
    return check_ratings(plant.model())


def _two_it(rating: str, span: str = "100") -> list[Finding]:
    """A on the 100 V IT supply `a`, P on the IT supply `b` whose rails are `span` V apart."""
    plant = Plant()
    supply(plant, "a", SQUARE_IT, name="a", earthing=IT)
    supply(plant, "b", {"P": rail(span, 0), "Q": rail(span, 60)}, name="b", earthing=IT)
    load(plant, "d", [("A",), ("P",)], rated(ac=rating))
    return list(_run(plant))


def test_two_it_rails_fire_on_the_cross_term_alone() -> None:
    """S1 = S2 = 10,000, V = 200 exactly: R = 199 fails `S1 + S2 > R^2` but 4 S1 S2 is above."""
    (finding,) = _two_it("199")
    assert "stand across it at 200 V (IT: no common reference" in finding.message
    assert _two_it("200") == []  # right at the boundary
    assert _two_it("201") == []


def test_it_earth_ac_takes_the_highest_pair_by_its_own_phases_not_the_first_pair() -> None:
    """A (10 V, 0 deg), B (50 V, 60 deg), C (50 V, 120 deg): A-C squares to 3,100, the highest
    of the three pairs, above A-B (2,100) and B-C (2,500). Dropping B's phase in the B-C pair
    (as if it were 0) would instead make B-C the highest, at 7,500.
    """
    points = ((Fraction(10), 0), (Fraction(50), 60), (Fraction(50), 120))
    assert voltage.it_earth(points, ac=True) == voltage.root(Fraction(3100))
