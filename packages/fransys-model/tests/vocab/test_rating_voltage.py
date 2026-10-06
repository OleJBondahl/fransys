"""`RATING_VOLTAGE_BELOW_CIRCUIT` on earthed supplies (decision model-0079, model review Q4).

The IT branches are in `test_rating_voltage_it.py`. Every model here is hand-built and invented.
`_findings` is how many findings a load on the named rails gets: 1 fires, 0 passes.
"""

import decimal
from decimal import Decimal
from fractions import Fraction
from typing import TYPE_CHECKING

import pytest
from plant import Plant
from rating_plant import AC_400, load, rail, rated, supply

from fransys_model.kernel import Finding, Severity, make_id
from fransys_model.vocab import (
    ALL_VALIDATORS,
    Operating,
    OperatingFacet,
    PartRatingFacet,
    Rating,
    RatingFacet,
    voltage,
)
from fransys_model.vocab.enums import Current
from fransys_model.vocab.supply_system import SupplySystem
from fransys_model.vocab.validators.ratings import RATING_VOLTAGE_BELOW_CIRCUIT, check_ratings
from fransys_model.vocab.validators.supplies import check_supplies

if TYPE_CHECKING:
    from collections.abc import Sequence

L1, L2, L3, N = ("L1",), ("L2",), ("L3",), ("N",)
HV = {"HV+": rail("400"), "HV-": rail("-400")}


def _run(plant: Plant) -> tuple[Finding, ...]:
    return check_ratings(plant.model())


def _findings(
    ports_on: Sequence[Sequence[str]], *, ac: str | None = None, dc: str | None = None
) -> int:
    """The finding count for a load on `ports_on`, beside an earthed AC supply and a DC pair."""
    plant = Plant()
    supply(plant, "ac", AC_400)
    supply(plant, "hv", HV, current=Current.DC)
    load(plant, "d", ports_on, rated(ac, dc))
    return len(_run(plant))


def test_a_three_pole_load_gets_an_error_naming_function_rating_rails_and_v() -> None:
    plant = Plant()
    supply(plant, "ac", AC_400)
    function = load(plant, "k", [L1, L2, L3], rated(ac="250"))
    (finding,) = _run(plant)
    assert finding.code == RATING_VOLTAGE_BELOW_CIRCUIT == "RATING_VOLTAGE_BELOW_CIRCUIT"
    assert finding.severity == Severity.ERROR
    assert finding.subjects == (function,)
    assert finding.message == (
        "function 'f' of item k is rated 250 V AC (part or template rating), "
        "but rails 'L1' and 'L2' stand across it at 398.4 V"
    )


@pytest.mark.parametrize(("rating", "count"), [("250", 1), ("398", 1), ("399", 0), ("400", 0)])
def test_l1_to_l3_stands_at_the_square_root_of_158700(rating: str, count: int) -> None:
    """158,700 is above 250 squared (62,500) and below 400 squared (160,000)."""
    assert _findings([L1, L2, L3], ac=rating) == count


@pytest.mark.parametrize("swap", [False, True])
@pytest.mark.parametrize(
    ("phase", "passes", "fires"),
    [(0, "0", None), (60, "100", "99"), (120, "174", "173"), (180, "200", "199"),
     (240, "174", "173"), (300, "100", "99"),
     (360, "0", None), (-60, "100", "99")],
)  # fmt: skip
def test_every_phase_angle_gives_its_own_voltage_in_either_rail_order(
    phase: int, passes: str, fires: str | None, *, swap: bool
) -> None:
    """Two 100 V rails `phase` degrees apart stand at 0, 100, 173.2, 200, 173.2, 100 V."""
    first, second = (phase, 0) if swap else (0, phase)
    rails = {"A": rail("100", first), "B": rail("100", second)}

    def count(rating: str) -> int:
        plant = Plant()
        supply(plant, "ac", rails)
        load(plant, "d", [("A",), ("B",)], rated(ac=rating))
        return len(_run(plant))

    assert count(passes) == 0
    assert fires is None or count(fires) == 1


@pytest.mark.parametrize(
    ("rating", "count"), [("360.55", 1), ("360.5551", 1), ("360.5552", 0), ("360.56", 0)]
)
def test_the_decision_never_uses_the_printed_value(rating: str, count: int) -> None:
    """P 300 V and Q 100 V at 120 degrees: V^2 = 130,000, V = 360.5551..., printed 360.6."""
    plant = Plant()
    supply(plant, "ac", {"P": rail("300", 0), "Q": rail("100", 120)})
    load(plant, "d", [("P",), ("Q",)], rated(ac=rating))
    assert len(_run(plant)) == count


@pytest.mark.parametrize(("rating", "count"), [("250", 0), ("230", 0), ("229.99", 1), ("229", 1)])
def test_a_lamp_on_l1_and_n_stands_at_230_and_equal_passes(rating: str, count: int) -> None:
    assert _findings([L1, N], ac=rating) == count


def test_a_firing_lamp_names_230_and_its_rails() -> None:
    plant = Plant()
    supply(plant, "ac", AC_400)
    load(plant, "lamp", [L1, N], rated(ac="229.99"))
    (finding,) = _run(plant)
    assert finding.message == (
        "function 'f' of item lamp is rated 229.99 V AC (part or template rating), "
        "but rails 'L1' and 'N' stand across it at 230 V"
    )


def test_a_30_digit_ac_rating_is_compared_exactly() -> None:
    """28-digit `Decimal` squares of rail and rating are equal: rounding would pass it."""
    high, rating = Decimal("10000000000000000000000000000.1"), "10000000000000000000000000000.0"
    assert not high * high > Decimal(rating) * Decimal(rating)  # the rounded answer flips
    plant = Plant()
    supply(plant, "ac", {"L1": rail(str(high), 0), "N": rail("0")})
    load(plant, "lamp", [L1, N], rated(ac=rating))
    assert len(_run(plant)) == 1
    equal = Plant()
    supply(equal, "ac", {"L1": rail(str(high), 0), "N": rail("0")})
    load(equal, "lamp", [L1, N], rated(ac=str(high)))
    assert _run(equal) == ()


def test_a_30_digit_dc_rating_is_compared_exactly() -> None:
    high, rating = Decimal("10000000000000000000000000000.5"), "10000000000000000000000000000.4"
    assert not abs(high - 0) > Decimal(rating)  # the 28-digit difference is rounded down
    plant = Plant()
    supply(plant, "dc", {"P": rail(str(high)), "Q": rail("0")}, current=Current.DC)
    load(plant, "d", [("P",), ("Q",)], rated(dc=rating))
    assert len(_run(plant)) == 1


def test_two_rails_at_one_port_are_alternatives_and_never_stand_across_the_load() -> None:
    """A changeover's common on L1 and L2, N at the other port: L1 to L2 (398 V) is no pair."""
    assert _findings([("L1", "L2"), N], ac="250") == 0
    assert _findings([("L1", "L2"), N], ac="229") == 1


def test_with_no_pair_the_rails_are_checked_to_earth_and_the_highest_is_named() -> None:
    assert _findings([("L1", "L2")], ac="250") == 0
    assert _findings([L1, L1], ac="250") == 0  # two ports on one rail: no second rail
    assert _findings([L1, L1], ac="220") == 1  # so 230 to earth, not an L1-L1 pair of 0 V
    plant = Plant()
    supply(plant, "ac", AC_400)
    load(plant, "c", [("L1", "L2")], rated(ac="220"))
    (finding,) = _run(plant)
    assert finding.message == (
        "function 'f' of item c is rated 220 V AC (part or template rating), "
        "but rail 'L1' is at 230 V to earth"
    )


def test_when_a_pair_exists_it_alone_decides_even_below_the_rails_to_earth() -> None:
    """L1 (230) and M (200) at one phase stand at 30 V: rated 100, no finding, though L1 is 230."""
    plant = Plant()
    supply(plant, "ac", {"L1": rail("230", 0), "M": rail("200", 0)})
    load(plant, "d", [L1, ("M",)], rated(ac="100"))
    assert _run(plant) == ()
    tight = Plant()
    supply(tight, "ac", {"L1": rail("230", 0), "M": rail("200", 0)})
    load(tight, "d", [L1, ("M",)], rated(ac="29"))
    (finding,) = _run(tight)
    assert finding.message.endswith("stand across it at 30 V")


@pytest.mark.parametrize(("rating", "count"), [("600", 1), ("799", 1), ("800", 0)])
def test_dc_plus_and_minus_400_stand_at_800(rating: str, count: int) -> None:
    assert _findings([("HV+",), ("HV-",)], dc=rating) == count


def test_a_dc_rail_at_minus_400_alone_is_400_to_earth() -> None:
    assert _findings([("HV-",)], dc="399") == 1
    assert _findings([("HV-",)], dc="400") == 0


def test_ac_and_dc_are_checked_on_their_own_rails_and_ratings() -> None:
    ports = [L1, N, ("HV+",), ("HV-",)]  # AC pair L1-N is 230; DC pair is 800
    assert _findings(ports, ac="250") == 0
    assert _findings(ports, ac="200") == 1
    assert _findings(ports, dc="700") == 1
    assert _findings(ports, dc="800") == 0
    assert _findings(ports, ac="250", dc="800") == 0
    assert _findings(ports, ac="250", dc="700") == 1
    assert _findings(ports, ac="200", dc="700") == 2


def test_a_rating_of_one_kind_ignores_rails_of_the_other_kind() -> None:
    """One AC rail and one DC rail at two ports: each kind has a single rail, to earth."""
    assert _findings([L1, ("HV+",)], ac="250") == 0
    assert _findings([L1, ("HV+",)], dc="300") == 1


def test_both_kinds_give_one_finding_each_in_sorted_order() -> None:
    plant = Plant()
    supply(plant, "ac", AC_400)
    supply(plant, "hv", HV, current=Current.DC)
    load(plant, "d", [L1, N, ("HV+",), ("HV-",)], rated(ac="200", dc="700"))
    findings = _run(plant)
    assert [f.message.split(" V ")[1][:2] for f in findings] == ["AC", "DC"]
    assert findings == tuple(sorted(findings, key=lambda f: (f.code, f.subjects, f.message)))


def test_no_rating_no_rail_or_no_supply_gives_nothing() -> None:
    unrated = Plant()
    supply(unrated, "ac", AC_400)
    load(unrated, "d", [L1, L2, L3], None)
    assert _run(unrated) == ()
    blank = Plant()
    supply(blank, "ac", AC_400)
    load(blank, "d", [L1, L2, L3], Rating())
    assert _run(blank) == ()
    assert _findings([("X",), ("Y",)], ac="1", dc="1") == 0  # potentials in no supply
    bare = Plant()
    load(bare, "d", [L1, L2, L3], rated(ac="1"))
    assert _run(bare) == ()
    assert _findings([L1, L2, L3], ac="250") == 1  # the same load does fire with a supply


def test_a_rail_reaches_a_function_through_a_wire() -> None:
    plant = Plant()
    supply(plant, "ac", AC_400)
    live, neutral = plant.pin("x1", "t", "1"), plant.pin("x1", "t", "2")
    plant.net("n-l1", (live,), potential="L1")
    plant.net("n-n", (neutral,), potential="N")
    function = load(plant, "lamp", [(), ()], rated(ac="200"))
    plant.wire(live, plant.pin("lamp", "f", "p0"), key="w1")
    plant.wire(neutral, plant.pin("lamp", "f", "p1"), key="w2")
    assert [f.subjects for f in _run(plant)] == [(function,)]


def _templated(
    *, template: Rating | None = None, part: Rating | None = None, operating: bool = False
) -> Plant:
    """A function on L1 and N whose template and part carry the given ratings, or an envelope."""
    plant = Plant()
    supply(plant, "ac", AC_400)
    part_record, fn_template, _first, _second = plant.relay_part()
    function = plant.function(plant.item("k", part=part_record.id), "f", template=fn_template.id)
    for index, name in enumerate(("L1", "N")):
        plant.net(f"k-{index}", (plant.port(function, f"p{index}"),), potential=name)
    if template is not None:
        key = ("t",)
        facet = RatingFacet(
            id=make_id(RatingFacet, key), key=key, subject=fn_template.id, rating=template
        )
        plant.add(facet)
    if part is not None:
        key = ("p",)
        part_facet = PartRatingFacet(
            id=make_id(PartRatingFacet, key), key=key, subject=part_record.id, rating=part
        )
        plant.add(part_facet)
    if operating:
        key = ("o",)
        envelope = Operating(voltage_ac_v=Decimal(10), max_voltage_v=Decimal(10))
        plant.add(
            OperatingFacet(
                id=make_id(OperatingFacet, key),
                key=key,
                subject=fn_template.id,
                operating=envelope,
            )
        )
    return plant


def test_an_operating_envelope_alone_never_fires_and_the_template_rating_wins() -> None:
    assert _run(_templated(operating=True)) == ()
    assert len(_run(_templated(template=rated(ac="10"), operating=True))) == 1
    assert len(_run(_templated(part=rated(ac="10")))) == 1  # the part's, with no template rating
    assert _run(_templated(template=rated(ac="250"), part=rated(ac="10"))) == ()


def _mixed() -> Plant:
    plant = Plant()
    supply(plant, "ac", AC_400)
    supply(plant, "hv", HV, current=Current.DC)
    load(plant, "a", [L1, L2, L3], rated(ac="250"))
    load(plant, "b", [("HV+",), ("HV-",)], rated(dc="600"))
    load(plant, "c", [L1, N], rated(ac="200", dc="1"))
    return plant


def test_findings_are_sorted_and_do_not_depend_on_the_record_order() -> None:
    plant = _mixed()
    findings = _run(plant)
    assert len(findings) == 3
    assert findings == tuple(sorted(findings, key=lambda f: (f.code, f.subjects, f.message)))
    backwards = Plant()
    backwards.add(*reversed(plant.records))
    assert _run(backwards) == findings


_SMALLER_ID, _LARGER_ID = sorted(("s1", "s2"), key=lambda key: make_id(SupplySystem, (key,)))


def _two_declarations(hundred: str, *, smaller_named: str, larger_named: str) -> Plant:
    """A potential `+X` in two supplies; the one keyed `hundred` says 100 V, the other 30 V.

    `smaller_named` and `larger_named` are the names of the supply with the smaller and the
    larger id, so a test can make the name order the opposite of the id order.
    """
    plant = Plant()
    for key, name in ((_SMALLER_ID, smaller_named), (_LARGER_ID, larger_named)):
        volts = "100" if key == hundred else "30"
        supply(plant, key, {"+X": rail(volts), "0V": rail("0")}, name=name, current=Current.DC)
    load(plant, "d", [("+X",)], rated(dc="50"))
    return plant


def test_a_potential_in_two_supplies_takes_the_smallest_name_not_the_smallest_id() -> None:
    """`POTENTIAL_IN_TWO_SUPPLIES` has fired; the supply named `aaa` wins with the larger id."""
    names = {"smaller_named": "zzz", "larger_named": "aaa"}
    by_name = _two_declarations(_LARGER_ID, **names)
    assert len(_run(by_name)) == 1  # aaa holds 100 V
    assert _run(_two_declarations(_SMALLER_ID, **names)) == ()  # aaa holds 30 V
    backwards = Plant()
    backwards.add(*reversed(by_name.records))
    assert _run(backwards) == _run(by_name)


def test_one_name_with_two_contents_takes_the_smallest_id() -> None:
    """`SUPPLY_DIFFERS` has fired; with one name the smaller id decides."""
    names = {"smaller_named": "dc", "larger_named": "dc"}
    plant = _two_declarations(_SMALLER_ID, **names)
    assert len(_run(plant)) == 1
    assert _run(_two_declarations(_LARGER_ID, **names)) == ()
    backwards = Plant()
    backwards.add(*reversed(plant.records))
    assert _run(backwards) == _run(plant)


def test_the_check_runs_in_all_validators_after_check_supplies() -> None:
    """Dropping `check_ratings` from `ALL_VALIDATORS` makes this fail."""
    model = _mixed().model()
    codes = {f.code for check in ALL_VALIDATORS for f in check(model)}
    assert RATING_VOLTAGE_BELOW_CIRCUIT in codes
    assert ALL_VALIDATORS.index(check_ratings) == ALL_VALIDATORS.index(check_supplies) + 1


def _rail_v(supply_name: str, *, ac: bool, it: bool) -> voltage.RailV:
    value = Fraction(230)
    return voltage.RailV("R", supply_name, it, ac, value, 0 if ac else None, voltage.exact(value))


def test_common_reference_needs_neither_side_ac_nor_it_even_when_only_one_side_is() -> None:
    """Two different supplies with only one side AC (and the mirrored case, only the other side
    AC): each disjunct is gated by `or`, so a lone AC or IT side must not be masked by the other
    side being calm.
    """
    assert (
        voltage.common_reference(_rail_v("x", ac=False, it=False), _rail_v("y", ac=True, it=False))
        is False
    )
    assert (
        voltage.common_reference(_rail_v("x", ac=True, it=False), _rail_v("y", ac=False, it=False))
        is False
    )


def test_ac_square_uses_the_phase_difference_not_the_sum() -> None:
    """100 V rails 60 degrees apart square to 10,000 (cos 60 degrees halves the cross term); the
    sum of the phases (180 degrees) would read cos 180 degrees and give 40,000 instead.
    """
    assert voltage._ac_square(Fraction(100), 120, Fraction(100), 60) == Fraction(10_000)


def test_ac_square_treats_a_declared_zero_phase_as_zero_not_as_the_missing_default() -> None:
    """0 degrees is falsy in Python, so `first_phase or 0` must resolve an explicit 0 to 0 by
    finding it already there, not fall through to a stand-in default that reads as 1 degree.
    """
    assert voltage._ac_square(Fraction(100), 0, Fraction(100), 1) == Fraction(10_000)


def test_exceeds_one_root_boundary_and_one_step_above() -> None:
    """3 + sqrt(4) is 5, exactly the rating: not above it. 3 + sqrt(4.01) is a hair over 5."""
    boundary = voltage.add(voltage.exact(Fraction(3)), voltage.root(Fraction(4)))
    assert voltage.exceeds(boundary, Fraction(5)) is False
    above = voltage.add(voltage.exact(Fraction(3)), voltage.root(Fraction(401, 100)))
    assert voltage.exceeds(above, Fraction(5)) is True


def test_exceeds_two_root_boundary_and_one_step_above() -> None:
    """Roots 0 and 4: sqrt(0) + sqrt(4) is 2, exactly the rating, with the second root alone
    deciding the OR's first term (`first + second`), since a zero root keeps the cross term at
    zero either way. Nudging that second root up to 4.01 must flip the decision; swapping the
    `+` for a `-`, or the boundary's `>` for `>=`, would not.
    """
    boundary = voltage.add(voltage.root(Fraction(0)), voltage.root(Fraction(4)))
    assert voltage.exceeds(boundary, Fraction(2)) is False
    above = voltage.add(voltage.root(Fraction(0)), voltage.root(Fraction(401, 100)))
    assert voltage.exceeds(above, Fraction(2)) is True


def test_magnitude_uses_60_digit_precision_not_the_ambient_default() -> None:
    """1/3 at 60 digits is 60 threes. The ambient context is forced to 28 digits here so the
    check does not depend on whatever precision an earlier test left active; `magnitude` must
    still get 60 by way of its own context, not by copying that ambient one.
    """
    with decimal.localcontext(decimal.Context(prec=28)):
        assert str(voltage.magnitude(voltage.exact(Fraction(1, 3)))) == "0." + "3" * 60


def test_decimal_divides_the_fraction_it_does_not_multiply_it() -> None:
    """1/3 to 60 digits is 60 threes; multiplying instead of dividing gives 3, not that."""
    with decimal.localcontext(decimal.Context(prec=60)):
        assert str(voltage._decimal(Fraction(1, 3))) == "0." + "3" * 60
