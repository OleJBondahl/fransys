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


def test_an_actuator_row_matches_only_the_three_phase_port_shape() -> None:
    from fransys_el.symbol_rules import Facts, default_row, port_shape

    def row(names: list[str]) -> str | None:
        found = default_row(
            Facts("actuator", None, None, None, None, actuator=True, port_shape=port_shape(names))
        )
        return None if found is None else found.symbol

    assert row(["U", "V", "W", "PE"]) == "motor-3ph-pe"
    assert row(["1", "2", "3", "4"]) is None
    assert row([]) is None
