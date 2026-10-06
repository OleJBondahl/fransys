"""`RATING_VOLTAGE_BELOW_CIRCUIT` with IT supplies (decision model-0079, model review Q4 and Q2).

An IT rail's voltage to earth is its supply's highest voltage between two of its own rails; a pair
across an IT supply and another has no common reference and stands at the sum of the two rails'
voltages to earth. Every model is hand-built and invented.
"""

from fractions import Fraction
from typing import TYPE_CHECKING

import pytest
from plant import Plant
from rating_plant import AC_400, load, rail, rated, supply

from fransys_model.vocab import voltage
from fransys_model.vocab.enums import Current, Earthing
from fransys_model.vocab.validators.ratings import check_ratings

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fransys_model.kernel import Finding
    from fransys_model.vocab.supply_system import Rail

EARTHED, IT = Earthing.EARTHED, Earthing.IT
DC_IT = {"DC+": rail("800"), "DC-": rail("0")}
# Two rails of 100 V at 0 and 60 degrees: 100 V apart, exactly, so a boundary can be hit.
SQUARE_IT = {"A": rail("100", 0), "B": rail("100", 60)}


def _run(plant: Plant) -> tuple[Finding, ...]:
    return check_ratings(plant.model())


def _dc(ports_on: Sequence[Sequence[str]], rating: str, earthing: Earthing) -> list[Finding]:
    """A load on the DC pair `DC+`/`DC-` (earthing `earthing`) and an earthed `+24V` rail."""
    plant = Plant()
    supply(plant, "dc", DC_IT, name="dcit", current=Current.DC, earthing=earthing)
    supply(plant, "aux", {"+24V": rail("24")}, current=Current.DC)
    load(plant, "d", ports_on, rated(dc=rating))
    return list(_run(plant))


def test_a_dc_rail_alone_is_its_own_potential_earthed_and_the_supplys_span_under_it() -> None:
    assert _dc([("DC-",)], "600", EARTHED) == []
    (finding,) = _dc([("DC-",)], "600", IT)
    assert finding.message == (
        "function 'f' of item d is rated 600 V DC (part or template rating), "
        "but rail 'DC-' is at 800 V to earth (IT supply 'dcit')"
    )


@pytest.mark.parametrize("earthing", [EARTHED, IT])
def test_both_rails_of_one_supply_stand_at_their_difference_earthed_or_not(
    earthing: Earthing,
) -> None:
    assert _dc([("DC+",), ("DC-",)], "800", earthing) == []
    assert len(_dc([("DC+",), ("DC-",)], "799", earthing)) == 1


def test_an_it_rail_and_an_earthed_supply_stand_at_the_sum_of_their_voltages_to_earth() -> None:
    ports = [("DC-",), ("+24V",)]
    assert _dc(ports, "800", EARTHED) == []  # earthed: |0 - 24| = 24
    (finding,) = _dc(ports, "800", IT)  # IT: 800 + 24
    assert finding.message == (
        "function 'f' of item d is rated 800 V DC (part or template rating), "
        "but rails '+24V' and 'DC-' stand across it at 824 V "
        "(IT: no common reference, the sum of their voltages to earth)"
    )
    assert _dc(ports, "824", IT) == []


def test_two_it_dc_supplies_stand_at_the_sum_of_their_spans() -> None:
    def run(rating: str) -> int:
        plant = Plant()
        supply(plant, "x", {"X+": rail("100"), "X-": rail("0")}, current=Current.DC, earthing=IT)
        supply(plant, "y", {"Y+": rail("50"), "Y-": rail("0")}, current=Current.DC, earthing=IT)
        load(plant, "d", [("X+",), ("Y+",)], rated(dc=rating))
        return len(_run(plant))

    assert (run("150"), run("149.99")) == (0, 1)


def _ac(ports_on: Sequence[Sequence[str]], rating: str, earthing: Earthing) -> list[Finding]:
    """A load on the 3-phase 400 V supply (earthing `earthing`)."""
    plant = Plant()
    supply(plant, "ac", AC_400, name="400V", earthing=earthing)
    load(plant, "d", ports_on, rated(ac=rating))
    return list(_run(plant))


def test_an_ac_rail_alone_checks_at_the_supplys_span_only_when_it() -> None:
    """On L1 alone, rated 250: 230 V earthed passes; IT spans L1 to L2 (V^2 158,700) and fires."""
    assert _ac([("L1",)], "250", EARTHED) == []
    (finding,) = _ac([("L1",)], "250", IT)
    assert finding.message == (
        "function 'f' of item d is rated 250 V AC (part or template rating), "
        "but rail 'L1' is at 398.4 V to earth (IT supply '400V')"
    )
    assert _ac([("L1",)], "399", IT) == []


def test_two_rails_of_one_it_supply_check_as_an_earthed_pair() -> None:
    assert _ac([("L1",), ("N",)], "230", IT) == []
    assert len(_ac([("L1",), ("N",)], "229", IT)) == 1


def _earthed_and_it(ports_on: Sequence[Sequence[str]], rating: str) -> list[Finding]:
    """An IT AC supply A/B (span 100 V) beside an earthed AC one with rails `C` 24 V and `D` 0."""
    plant = Plant()
    supply(plant, "it", SQUARE_IT, name="it", earthing=IT)
    supply(plant, "ctl", {"C": rail("24", 0), "D": rail("0")}, name="ctl")
    load(plant, "d", ports_on, rated(ac=rating))
    return list(_run(plant))


def test_an_earthed_rail_above_the_rating_fires_at_once() -> None:
    """Eb = 24 > R = 20 with a span of 1 V: only `Eb > R` fires, as S = 1 is not above (20-24)^2."""

    def run(rating: str) -> list[Finding]:
        plant = Plant()
        supply(plant, "tiny", {"A": rail("1", 0), "B": rail("1", 60)}, name="tiny", earthing=IT)
        supply(plant, "ctl", {"C": rail("24", 0), "D": rail("0")}, name="ctl")
        load(plant, "d", [("A",), ("C",)], rated(ac=rating))
        return list(_run(plant))

    (finding,) = run("20")
    assert "stand across it at 25 V" in finding.message
    assert run("25") == []  # 25 is the sum, and the squares form is False too


def test_an_it_and_an_earthed_rail_fire_on_the_squares_when_eb_is_below_the_rating() -> None:
    """S = 10,000 and Eb = 24: R = 123.99 gives S > (R - Eb)^2, R = 124 is exactly equal."""
    ports = [("A",), ("C",)]
    assert len(_earthed_and_it(ports, "123.99")) == 1
    assert _earthed_and_it(ports, "124") == []
    assert _earthed_and_it(ports, "125") == []
    assert len(_earthed_and_it(ports, "100")) == 1


def test_the_l1_it_rail_and_an_earthed_rail_sum_with_an_irrational_root() -> None:
    """sqrt(158,700) + 24 is about 422.37: R = 422 fires, 423 passes."""

    def run(rating: str) -> int:
        plant = Plant()
        supply(plant, "it", AC_400, name="400V", earthing=IT)
        supply(plant, "ctl", {"C": rail("24", 0), "D": rail("0")}, name="ctl")
        load(plant, "d", [("L1",), ("C",)], rated(ac=rating))
        return len(_run(plant))

    assert (run("422"), run("423")) == (1, 0)


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


def test_two_it_rails_fire_on_the_sum_of_the_squares_alone() -> None:
    """S1 = 10,000, S2 = 1, V = 101: at R = 1 the cross form (40,000 > 10,000^2) is False."""
    (finding,) = _two_it("1", span="1")
    assert "stand across it at 101 V" in finding.message
    assert _two_it("101", span="1") == []


def test_a_supply_with_one_rail_is_its_own_voltage_to_earth_it_or_not() -> None:
    """No pair of its own rails, so the rail's |max_v|: AC 230 and DC -400, alone and summed."""

    def run(
        current: Current, rails: dict[str, Rail], ports: Sequence[Sequence[str]], r: str
    ) -> int:
        plant = Plant()
        supply(plant, "solo", rails, name="solo", current=current, earthing=IT)
        supply(plant, "aux", {"C": rail("24", 0)}, name="aux", current=current)
        rating = rated(ac=r) if current is Current.AC else rated(dc=r)
        load(plant, "d", ports, rating)
        return len(_run(plant))

    ac, dc = {"L": rail("230", 0)}, {"M": rail("-400")}
    assert (run(Current.AC, ac, [("L",)], "230"), run(Current.AC, ac, [("L",)], "229")) == (0, 1)
    assert (run(Current.DC, dc, [("M",)], "400"), run(Current.DC, dc, [("M",)], "399")) == (0, 1)
    both = [("L",), ("C",)]  # 230 to earth plus the earthed 24: 254
    assert (run(Current.AC, ac, both, "254"), run(Current.AC, ac, both, "253")) == (0, 1)
    both = [("M",), ("C",)]  # 400 plus 24
    assert (run(Current.DC, dc, both, "424"), run(Current.DC, dc, both, "423")) == (0, 1)


def test_it_earth_is_none_below_two_points() -> None:
    assert voltage.it_earth((), ac=True) is None
    assert voltage.it_earth(((Fraction(230), 0),), ac=False) is None


def test_it_earth_ac_takes_the_highest_pair_by_its_own_phases_not_the_first_pair() -> None:
    """A (10 V, 0 deg), B (50 V, 60 deg), C (50 V, 120 deg): A-C squares to 3,100, the highest
    of the three pairs, above A-B (2,100) and B-C (2,500). Dropping B's phase in the B-C pair
    (as if it were 0) would instead make B-C the highest, at 7,500.
    """
    points = ((Fraction(10), 0), (Fraction(50), 60), (Fraction(50), 120))
    assert voltage.it_earth(points, ac=True) == voltage.root(Fraction(3100))


def test_it_earth_dc_takes_the_highest_pairwise_difference_not_the_first_pair() -> None:
    """-100 V, 5 V, 10 V: the highest pairwise spread is |-100 - 10| = 110, above |-100 - 5| = 105
    and |5 - 10| = 5. Adding instead of subtracting would instead make -100/5 the highest, at 95.
    """
    points = ((Fraction(-100), None), (Fraction(5), None), (Fraction(10), None))
    assert voltage.it_earth(points, ac=False) == voltage.exact(Fraction(110))
