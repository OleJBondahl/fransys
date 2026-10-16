"""`chosen_point`: which breaking point D is checked at."""

from decimal import Decimal

from fransys_model.derive.facts.fault.breaking import chosen_point
from fransys_model.vocab.ratings import BreakingPoint

_LOW = BreakingPoint(voltage_v=Decimal(400), current_a=Decimal(3000))
_HIGH = BreakingPoint(voltage_v=Decimal(800), current_a=Decimal(900))


def test_the_lowest_voltage_at_or_above_the_circuit_wins() -> None:
    assert chosen_point((_LOW, _HIGH), Decimal(600), None) == _HIGH
    assert chosen_point((_HIGH, _LOW), Decimal(400), None) == _LOW


def test_a_point_below_the_sources_time_constant_is_short_of_time_constant() -> None:
    point = BreakingPoint(
        voltage_v=Decimal(1000), current_a=Decimal(15000), time_constant_ms=Decimal(15)
    )
    assert chosen_point((point,), Decimal(60), Decimal(20)) == "time constant"
    assert chosen_point((point,), Decimal(60), Decimal(15)) == point
