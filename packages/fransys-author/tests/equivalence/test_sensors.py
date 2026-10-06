"""EA12 pair 1: 16 sensors from a dict, typed and untyped, against today's engine."""

from typing import TYPE_CHECKING, ClassVar

import pytest
from fransys_author import Design
from fransys_author.surface import Fn, Pin, TypedDevice, TypedFn, design
from fransys_author.surface.colours import BU

if TYPE_CHECKING:
    from fransys_model.kernel import Draft

SENSORS = {f"B{i}": 17 - i for i in range(1, 17)}  # sensor tag -> its terminal, reversed


class SensorFn(TypedFn):
    OUT: Pin


class Sensor(TypedDevice):
    mpn: ClassVar[str] = "TEST-SENSOR"
    sensor: SensorFn


def untyped(lib: Draft) -> Draft:
    d = design(lib, place="C1")
    with d.function("SENS", "Sensors"):
        x1 = d.terminal_strip("X1", "TEST-TB")
        for tag, n in SENSORS.items():
            s = d.device(tag, "TEST-SENSOR")
            d.wire(s.sensor.OUT, x1[n], wire=(BU, 0.75))
    return d.draft()


def typed(lib: Draft) -> Draft:
    d = design(lib, place="C1")
    with d.function("SENS", "Sensors"):
        x1 = d.terminal_strip("X1", "TEST-TB")
        for tag, n in SENSORS.items():
            s = d.device(tag, Sensor)
            d.wire(s.sensor.OUT, x1[n], wire=(BU, 0.75))
    return d.draft()


def engine(lib: Draft) -> Draft:
    e = Design(lib)
    c1, g = e.location("C1"), e.group("SENS", "Sensors")
    x1 = e.strip("X1", at=c1)
    wire = e.wiring(colour="BU", gauge="0.75")
    for tag, n in SENSORS.items():
        s = e.item("TEST-SENSOR", name=f"SENS/{tag}", tag=tag, at=c1, group=g)
        wire(s.fn("sensor")["OUT"], x1.terminal("TEST-TB", index=n, group=g).inner)
    return e.draft()


def test_typed_untyped_and_engine_build_one_model(library: Draft, same_model) -> None:
    same_model(library, engine, untyped, typed)


def test_the_typed_class_gives_a_function_handle_not_a_bare_pin(library: Draft) -> None:
    d = design(library)
    assert isinstance(d.device("B1", Sensor).sensor, Fn)


def test_a_sensor_wired_to_the_wrong_terminal_is_another_model(library: Draft, same_model) -> None:
    def swapped(lib: Draft) -> Draft:
        d = design(lib, place="C1")
        with d.function("SENS", "Sensors"):
            x1 = d.terminal_strip("X1", "TEST-TB")
            for tag, n in SENSORS.items():
                traded = {16: 15, 15: 16}.get(n, n)  # the two last sensors trade terminals
                s = d.device(tag, "TEST-SENSOR")
                d.wire(s.sensor.OUT, x1[traded], wire=(BU, 0.75))
        return d.draft()

    with pytest.raises(pytest.fail.Exception, match=r"script 2 builds another model"):
        same_model(library, engine, swapped)


def test_the_helper_names_the_first_differing_records(library: Draft, same_model) -> None:
    def short(lib: Draft) -> Draft:
        d = design(lib, place="C1")
        d.terminal_strip("X1", "TEST-TB")
        return d.draft()

    with pytest.raises(pytest.fail.Exception) as err:
        same_model(library, untyped, short)
    assert "only in A:" in str(err.value)
