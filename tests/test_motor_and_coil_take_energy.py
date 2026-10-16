"""A supply's load sum counts a motor's and a coil's current (spec API-CLARITY C6.7, A9).

A motor and a coil draw from their supply as a lamp does: `actuator` and `coil` take energy by
default, so `load_limits` lists them once the part states a draw. A part may still state `energy`.
"""

from decimal import Decimal

import fransys_parts
from fransys_author import Design
from ratings_fixtures import freeze_design, line_motor

from fransys_model.derive import load_limits
from fransys_model.derive.facts.energy_flow import takes_energy
from fransys_model.vocab.enums import Current


def test_a_motor_on_the_mains_is_in_the_load_sum_with_its_stated_current() -> None:
    model, p = line_motor()
    motor = p["m1"].fn("motor").id
    assert takes_energy(model, motor)
    found = [limit for limit in load_limits(model) if limit.function == motor]
    assert len(found) == 3
    assert {(limit.kind, limit.draw_a) for limit in found} == {(Current.AC, Decimal(8))}


def test_a_relay_coil_on_a_24_volt_supply_is_in_the_load_sum() -> None:
    d = Design(fransys_parts.load("demo_parts"))
    d.supply("24V", current="dc", rails={"P24": ("24", None), "M": ("0", None)})
    coil = d.item("DEMO-RLY-2CO-24", name="k1").fn("coil")
    d.net("P24", coil["A1"], cls="power", potential="P24")
    d.net("M", coil["A2"], cls="power", potential="M")
    model = freeze_design(d)
    assert takes_energy(model, coil.id)
    found = [limit for limit in load_limits(model) if limit.function == coil.id]
    assert [(limit.kind, limit.draw_a) for limit in found] == [(Current.DC, Decimal("0.015"))]
