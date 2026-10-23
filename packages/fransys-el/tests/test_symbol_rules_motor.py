"""SYMBOL-RULES E (Ruling 68 A1): a motor is drawn as `motor-3ph-pe` by the symbol kit."""

import fransys as fr
from fransys_el import symbol_kit

from electrical_symbols import LIBRARY


def test_a_motor_draws_as_the_three_phase_motor_with_pe() -> None:
    d = fr.design("demo_parts")
    m = d.device("M1", "DEMO-MOTOR-4KW")
    kit = symbol_kit(fr.build(d).model, LIBRARY)
    assert kit[m.motor.id].key == "motor-3ph-pe"


def test_the_star_delta_motors_start_winding_is_the_motor_and_its_end_stays_a_box() -> None:
    d = fr.design("demo_parts")
    m = d.device("M2", "DEMO-MOTOR-11KW-YD")
    kit = symbol_kit(fr.build(d).model, LIBRARY)
    assert kit[m.start.id].key == "motor-3ph-pe"
    assert m.end.id not in kit or kit[m.end.id].key != "motor-3ph-pe"
