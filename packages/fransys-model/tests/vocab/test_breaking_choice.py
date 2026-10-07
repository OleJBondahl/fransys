"""`chosen_point`: the breaking point D is checked at (RATINGS-3 R10, R11, acceptance 4 and 5)."""

from decimal import Decimal

from fransys_model.vocab.breaking_choice import chosen_point
from fransys_model.vocab.ratings import BreakingPoint

_LOW = BreakingPoint(voltage_v=Decimal(400), current_a=Decimal(3000))
_HIGH = BreakingPoint(voltage_v=Decimal(800), current_a=Decimal(900))


def test_the_lowest_voltage_at_or_above_the_circuit_wins() -> None:
    assert chosen_point((_LOW, _HIGH), Decimal(600), None) == _HIGH
    assert chosen_point((_HIGH, _LOW), Decimal(400), None) == _LOW


def test_no_point_at_or_above_the_circuit_voltage_is_short_of_voltage() -> None:
    assert chosen_point((_LOW, _HIGH), Decimal(900), None) == "voltage"


def test_a_point_below_the_sources_time_constant_is_short_of_time_constant() -> None:
    point = BreakingPoint(
        voltage_v=Decimal(1000), current_a=Decimal(15000), time_constant_ms=Decimal(15)
    )
    assert chosen_point((point,), Decimal(60), Decimal(20)) == "time constant"
    assert chosen_point((point,), Decimal(60), Decimal(15)) == point


def test_an_unknown_time_constant_leaves_only_points_without_one() -> None:
    timed = BreakingPoint(
        voltage_v=Decimal(100), current_a=Decimal(9000), time_constant_ms=Decimal(5)
    )
    assert chosen_point((timed, _HIGH), Decimal(60), None) == _HIGH
    assert chosen_point((timed,), Decimal(60), None) == "time constant"


def test_a_point_without_a_time_constant_applies_at_any_time_constant() -> None:
    assert chosen_point((_LOW,), Decimal(60), Decimal(50)) == _LOW


def test_a_tie_in_voltage_takes_the_lower_current() -> None:
    other = BreakingPoint(voltage_v=Decimal(400), current_a=Decimal(2000))
    assert chosen_point((_LOW, other), Decimal(230), None) == other
