"""EA14: the easy level (written out) and the efficient level (a function, a loop) are one model."""

from typing import TYPE_CHECKING

from fransys_author.surface import Design, design
from fransys_author.surface.colours import BU

if TYPE_CHECKING:
    from fransys_model.kernel import Draft

TABLE = {"B1": 3, "B2": 1, "B3": 2}


def easy(lib: Draft) -> Draft:
    d = design(lib, place="C1")
    with d.function("SENS", "Sensors"):
        x1 = d.terminal_strip("X1", "TEST-TB")
        b1 = d.device("B1", "TEST-SENSOR")
        d.wire(b1.sensor.OUT, x1[3], wire=(BU, 0.75))
        b2 = d.device("B2", "TEST-SENSOR")
        d.wire(b2.sensor.OUT, x1[1], wire=(BU, 0.75))
        b3 = d.device("B3", "TEST-SENSOR")
        d.wire(b3.sensor.OUT, x1[2], wire=(BU, 0.75))
    return d.draft()


def _sensor(d: Design, x1, tag: str, number: int) -> None:
    s = d.device(tag, "TEST-SENSOR")
    d.wire(s.sensor.OUT, x1[number], wire=(BU, 0.75))


def efficient(lib: Draft) -> Draft:
    d = design(lib, place="C1")
    with d.function("SENS", "Sensors"):
        x1 = d.terminal_strip("X1", "TEST-TB")
        for tag, number in TABLE.items():
            _sensor(d, x1, tag, number)
    return d.draft()


def test_a_function_and_a_loop_build_the_written_out_circuit(library: Draft, same_model) -> None:
    same_model(library, easy, efficient)
